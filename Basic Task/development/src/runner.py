#!/usr/bin/env python3
"""
runner.py —— 固定负载运行器

用法：
    python3 src/runner.py                       只拼装不发送，核查输入（dry-run）
    python3 src/runner.py run                   跑一遍负载（1 轮、并发 1）
    python3 src/runner.py run 3 1               跑 3 轮、并发 1
    python3 src/runner.py run 3 4               跑 3 轮、并发 4

指标定义见 configs/metrics.md。

设计原则：
  1. 路径全部由"本文件在哪里"推算，不写死绝对路径；
  2. 输入与生成参数全部取自 configs/workload.json；
  3. 一律使用流式，才能测到首字延迟（TTFT）；
  4. 成功与失败都落盘，失败不被覆盖。
"""

import json
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------
DEV_DIR = Path(__file__).resolve().parent.parent          # .../Basic Task/development
CONFIG_PATH = DEV_DIR / "configs" / "workload.json"
INPUT_DIR = DEV_DIR.parent / "提示词与输入文档" / "输入文档"
RUNS_DIR = DEV_DIR / "results" / "runs"

# ---------------------------------------------------------------------------
# 服务配置
# ---------------------------------------------------------------------------
SERVER_URL = "http://127.0.0.1:8888/v1/chat/completions"
TIMEOUT_SECONDS = 600

CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
WRITE_LOCK = threading.Lock()


def capture_env():
    """采集显卡当前状态。

    为什么要采：性能测量必须能说清"当时的环境"。
    电池供电、未升频、后台占卡都会让结果差出好几倍，
    事后无法从响应时间反推，只能在测量时留下记录。
    """
    query = "temperature.gpu,clocks.current.graphics,clocks.max.graphics,power.draw,utilization.gpu,memory.used"
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=" + query, "--format=csv,noheader"],
            capture_output=True, text=True, timeout=15, check=True).stdout.strip()
    except Exception as exc:                                  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}

    keys = ["temperature_c", "clock_mhz", "clock_max_mhz", "power_w", "util_percent", "vram_used_mib"]
    values = [v.strip() for v in out.split(",")]
    return dict(zip(keys, values))


def warm_up(rounds=2):
    """预热：先发几条请求丢掉。

    两个作用：让显卡从节能频率升上来（约需 6~8 秒），
    并让服务端完成算子加载与计算图捕获。
    """
    print("预热中（结果丢弃，不计入统计）……")
    task = CONFIG["tasks"][0]
    for _ in range(rounds):
        try:
            call_model(build_messages(task), 64)
        except Exception:                                     # noqa: BLE001
            pass
    print("预热完成")
    print()


# ===========================================================================
# 一、拼装输入
# ===========================================================================

def read_input_file(task):
    """读出任务关联的资料全文；没有关联资料时返回 None。"""
    if not task["file"]:
        return None
    return (INPUT_DIR / task["file"]).read_text(encoding="utf-8")


def build_messages(task):
    """把一条任务拼装成要发给模型的消息列表。

    固定两条：先 system（规则），后 user（资料 + 任务）。
    资料放在任务之前，使同一份资料的多个任务共享相同前缀。
    """
    file_content = read_input_file(task)

    if file_content is None:
        user_content = CONFIG["user_template_no_file"].format(prompt=task["prompt"])
    else:
        user_content = CONFIG["user_template"].format(
            file_name=task["file"],
            file_sha256=task["file_sha256"],
            file_content=file_content,
            prompt=task["prompt"],
        )

    return [
        {"role": "system", "content": CONFIG["system_message"]},
        {"role": "user", "content": user_content},
    ]


# ===========================================================================
# 二、输入核查（dry-run）
# ===========================================================================

def print_task_list():
    print("任务清单")
    print("-" * 78)
    for task in CONFIG["tasks"]:
        line = f"{task['id']:<5}{task['title']:<10} 输出上限 {task['max_tokens']:>5}"
        content = read_input_file(task)
        if content is not None:
            line += f"   资料：{task['file']}（{len(content)} 字符）"
        print(line)


def dry_run(only_ids=None):
    tasks = CONFIG["tasks"]
    if only_ids:
        tasks = [t for t in tasks if t["id"] in only_ids]

    print()
    print(f"负载版本 {CONFIG['workload_version']}　冻结于 {CONFIG['frozen_at']}　"
          f"任务总数 {len(CONFIG['tasks'])}")
    print("=" * 78)

    for task in tasks:
        system_msg, user_msg = build_messages(task)
        print(f"[{task['id']}] {task['title']}"
              f"（{task['type']} / {task['mode']} / 输出上限 {task['max_tokens']}）")
        print(f"  关联资料 : {task['file'] or '（无）'}")
        print(f"  [0] role={system_msg['role']:<7} 长度 {len(system_msg['content'])}")
        print(f"  [1] role={user_msg['role']:<7} 长度 {len(user_msg['content'])}")
        print(f"      开头 : {user_msg['content'][:40]!r}")
        if task["file"]:
            pos_doc = user_msg["content"].find("【资料】")
            pos_task = user_msg["content"].find("【任务】")
            order = "顺序正确" if 0 <= pos_doc < pos_task else "顺序异常"
            print(f"      顺序 : 【资料】@{pos_doc}　【任务】@{pos_task}　→ {order}")
        print()


# ===========================================================================
# 三、发送请求（流式，测量 TTFT）
# ===========================================================================

def call_model(messages, max_tokens):
    """流式发送一次请求。

    返回一个字典，含：answer / ttft_seconds / elapsed / usage / timings / finish_reason
    失败时抛出异常，由调用方记录。
    """
    generation = CONFIG["generation"]
    body = {
        "model": "local",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": generation["temperature"],
        "top_p": generation["top_p"],
        "seed": generation["seed"],
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": {"enable_thinking": generation["enable_thinking"]},
    }

    request = urllib.request.Request(
        SERVER_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    # 用单调时钟计时：time.time() 是墙上时钟，会被系统校时（NTP）拉动，
    # 曾实测出现负的 TTFT（-0.008 秒）。monotonic 只增不减，适合测时间间隔。
    started = time.monotonic()
    ttft = None
    pieces = []
    usage = {}
    timings = None
    finish_reason = None

    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8").strip()
            if not line.startswith("data: "):
                continue                     # 空行、注释行一律跳过
            payload = line[len("data: "):]
            if payload == "[DONE]":
                break

            chunk = json.loads(payload)

            if chunk.get("choices"):
                choice = chunk["choices"][0]
                delta = choice.get("delta") or {}
                text = delta.get("content")
                if text:
                    if ttft is None:
                        ttft = time.monotonic() - started  # 第一个非空内容到达
                    pieces.append(text)
                if choice.get("finish_reason"):
                    finish_reason = choice["finish_reason"]

            if chunk.get("usage"):
                usage = chunk["usage"]
            if chunk.get("timings"):
                timings = chunk["timings"]

    elapsed = time.monotonic() - started

    return {
        "answer": "".join(pieces),
        "ttft_seconds": ttft,
        "elapsed": elapsed,
        "usage": usage,
        "timings": timings,
        "finish_reason": finish_reason,
    }


def run_one_task(task, run_id, round_no, index, concurrency):
    """跑一条任务，返回一条完整记录（成功或失败都返回）。"""
    messages = build_messages(task)
    started_epoch = time.time()      # 这里要的是"绝对时刻"，墙上时钟正合适

    record = {
        "run_id": run_id,
        "request_id": f"{run_id}-{task['id']}-r{round_no}",
        "round": round_no,
        "seq": index,
        "concurrency": concurrency,
        "task_id": task["id"],
        "task_title": task["title"],
        "task_type": task["type"],
        "mode": task["mode"],
        "file": task["file"],
        "file_sha256": task["file_sha256"],
        "max_tokens": task["max_tokens"],
        "input_chars": sum(len(m["content"]) for m in messages),
        "status": None,
        "error": None,
        "answer": None,
        "finish_reason": None,
        "ttft_seconds": None,
        "client_seconds": None,
        "tpot_seconds": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "cached_tokens": None,
        "server_timings": None,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "started_epoch": round(started_epoch, 4),
        "finished_epoch": None,
    }

    try:
        result = call_model(messages, task["max_tokens"])
        usage = result["usage"] or {}
        completion = usage.get("completion_tokens")

        # 完整的流式响应最后一定会带一个 usage 分片。
        # 收不到它，说明流被中途掐断（例如服务端因容量不足取消了任务），
        # 这种响应必须单独标记，绝不能混进正常结果里。
        if not usage:
            record["status"] = "incomplete"
            record["error"] = "未收到结束分片（usage 缺失），响应可能被中断"
        else:
            record["status"] = "ok"

        record["answer"] = result["answer"]
        record["finish_reason"] = result["finish_reason"]
        record["ttft_seconds"] = round(result["ttft_seconds"], 3) if result["ttft_seconds"] else None
        record["client_seconds"] = round(result["elapsed"], 3)
        record["prompt_tokens"] = usage.get("prompt_tokens")
        record["completion_tokens"] = completion
        record["cached_tokens"] = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
        record["server_timings"] = result["timings"]

        if record["status"] == "ok" and result["ttft_seconds"] and completion and completion > 1:
            decode = result["elapsed"] - result["ttft_seconds"]
            record["tpot_seconds"] = round(decode / (completion - 1), 4)
    except urllib.error.HTTPError as exc:
        record["status"] = "http_error"
        record["error"] = exc.read().decode("utf-8", "replace")[:500]
    except Exception as exc:                                  # noqa: BLE001
        record["status"] = "failed"
        record["error"] = f"{type(exc).__name__}: {exc}"

    record["finished_epoch"] = round(time.time(), 4)
    return record


# ===========================================================================
# 四、跑完整负载
# ===========================================================================

def run_workload(rounds=1, concurrency=1):
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = RUNS_DIR / f"{run_id}.jsonl"
    env_path = RUNS_DIR / f"{run_id}.env.json"

    env_before = capture_env()

    print(f"运行编号：{run_id}")
    print(f"记录文件：{out_path}")
    print(f"轮次：{rounds}　并发：{concurrency}　任务数：{len(CONFIG['tasks'])}")
    print(f"显卡状态：{env_before.get('clock_mhz', '?')} / {env_before.get('clock_max_mhz', '?')}"
          f"　{env_before.get('power_w', '?')}　{env_before.get('temperature_c', '?')}")
    print()

    warm_up()                                     # 先热身，再开始计时

    env_after_warmup = capture_env()
    print("=" * 78)

    records = []
    tasks = CONFIG["tasks"]

    with out_path.open("w", encoding="utf-8") as out:
        for round_no in range(1, rounds + 1):
            jobs = [(i, t) for i, t in enumerate(tasks, start=1)]

            def work(job):
                index, task = job
                rec = run_one_task(task, run_id, round_no, index, concurrency)
                with WRITE_LOCK:                 # 多线程写同一文件，必须加锁
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    out.flush()
                    records.append(rec)
                    if rec["status"] == "ok":
                        print(f"  [轮{round_no} {index:>2}/{len(tasks)}] {task['id']}  "
                              f"TTFT {rec['ttft_seconds']:>6.2f}s  "
                              f"总 {rec['client_seconds']:>7.2f}s  "
                              f"输出 {rec['completion_tokens']:>4} token  "
                              f"{rec['finish_reason']}")
                    else:
                        ttft = rec["ttft_seconds"]
                        ttft_text = f"{ttft:>6.2f}s" if ttft is not None else "    -- s"
                        total = rec["client_seconds"]
                        total_text = f"{total:>7.2f}s" if total is not None else "     -- s"
                        print(f"  [轮{round_no} {index:>2}/{len(tasks)}] {task['id']}  "
                              f"TTFT {ttft_text}  总 {total_text}  "
                              f"!! {rec['status']}：{str(rec['error'])[:60]}")
                return rec

            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                list(pool.map(work, jobs))

    env_after = capture_env()
    env_path.write_text(json.dumps({
        "run_id": run_id,
        "rounds": rounds,
        "concurrency": concurrency,
        "gpu_before": env_before,
        "gpu_after_warmup": env_after_warmup,
        "gpu_after_run": env_after,
        "note": "电池供电或未升频会显著降低速度；本文件用于说明测量时的环境状态。",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print_summary(records, run_id, out_path, rounds, concurrency)
    print(f"环境快照：{env_path}")
    return records


def percentile(values, p):
    """线性插值的分位数。"""
    if not values:
        return None
    data = sorted(values)
    k = (len(data) - 1) * p
    low = int(k)
    high = min(low + 1, len(data) - 1)
    if low == high:
        return data[low]
    return data[low] + (data[high] - data[low]) * (k - low)


def num(value, digits=2):
    """把可能为 None 的数值格式化成字符串，避免格式化报错。"""
    return "--" if value is None else f"{value:.{digits}f}"


def print_summary(records, run_id, out_path, rounds, concurrency):
    ok = [r for r in records if r["status"] == "ok"]
    failed = [r for r in records if r["status"] != "ok"]

    print()
    print("=" * 78)
    print(f"汇总　运行编号 {run_id}　轮次 {rounds}　并发 {concurrency}")
    print("-" * 78)

    if not ok:
        print(f"成功 0 / 失败 {len(failed)}")
        print(f"原始记录：{out_path}")
        return

    ttfts = [r["ttft_seconds"] for r in ok if r["ttft_seconds"]]
    totals = [r["client_seconds"] for r in ok]
    tpots = [r["tpot_seconds"] for r in ok if r["tpot_seconds"]]
    out_tokens = sum(r["completion_tokens"] or 0 for r in ok)
    total_seconds = sum(totals)

    # 墙钟时间：从第一个请求发出，到最后一个请求结束的**真实**时间。
    # 并发场景下必须用它算吞吐；用"各请求耗时之和"会把并发算成负收益。
    wall_seconds = max(r["finished_epoch"] for r in records) - min(r["started_epoch"] for r in records)

    print(f"成功 {len(ok)} / 失败 {len(failed)}")
    print(f"TTFT     中位数 {num(percentile(ttfts, 0.5))}s   P95 {num(percentile(ttfts, 0.95))}s"
          f"   最小 {num(min(ttfts) if ttfts else None)}s   最大 {num(max(ttfts) if ttfts else None)}s")
    print(f"总耗时   中位数 {num(percentile(totals, 0.5))}s   P95 {num(percentile(totals, 0.95))}s"
          f"   最小 {num(min(totals) if totals else None)}s   最大 {num(max(totals) if totals else None)}s")
    print(f"TPOT     中位数 {num(percentile(tpots, 0.5), 4)}s   P95 {num(percentile(tpots, 0.95), 4)}s")
    print(f"输出     合计 {out_tokens} token")
    print(f"墙钟时间 {wall_seconds:.1f}s　"
          f"系统吞吐 {out_tokens / wall_seconds:.1f} token/秒"
          f"　（参考：各请求耗时之和 {total_seconds:.1f}s）")
    print()
    print(f"{'任务':<6}{'次数':>5}{'TTFT中位':>10}{'总耗时中位':>11}{'输出token':>10}{'缓存命中':>9}")
    for task in CONFIG["tasks"]:
        rows = [r for r in ok if r["task_id"] == task["id"]]
        if not rows:
            continue
        t = [r["ttft_seconds"] for r in rows if r["ttft_seconds"]]
        c = [r["client_seconds"] for r in rows]
        o = [r["completion_tokens"] or 0 for r in rows]
        k = [r["cached_tokens"] or 0 for r in rows]
        print(f"{task['id']:<6}{len(rows):>5}{num(percentile(t, 0.5)):>10}"
              f"{num(percentile(c, 0.5)):>11}{sum(o):>10}{sum(k):>9}")

    print("-" * 78)
    print(f"原始记录：{out_path}")


# ===========================================================================
# 入口
# ===========================================================================

def main():
    argv = sys.argv[1:]
    mode = argv[0] if argv else "dry"

    if mode == "dry":
        print_task_list()
        dry_run(["P01", "D01"])
        return 0

    if mode == "run":
        rounds = int(argv[1]) if len(argv) > 1 else 1
        concurrency = int(argv[2]) if len(argv) > 2 else 1
        run_workload(rounds=rounds, concurrency=concurrency)
        return 0

    print("用法：python3 src/runner.py [run [轮次] [并发]]")
    print("  python3 src/runner.py            只拼装不发送（输入核查）")
    print("  python3 src/runner.py run        1 轮、并发 1")
    print("  python3 src/runner.py run 3 1    3 轮、并发 1")
    print("  python3 src/runner.py run 3 4    3 轮、并发 4")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
