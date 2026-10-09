#!/usr/bin/env python3
"""
runner.py —— 固定负载运行器

两种用法：
    python3 src/runner.py        只拼装、不发送，打印出来核查输入（dry-run）
    python3 src/runner.py run    真正跑一遍负载，逐条记录到 results/runs/

设计原则：
  1. 路径全部由"本文件在哪里"推算，不写死绝对路径；
  2. 输入与生成参数全部取自 configs/workload.json，程序本身不掺入取值；
  3. 成功和失败都要落盘，失败不能被后续结果覆盖。
"""

import json
import sys
import time
import urllib.error
import urllib.request
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
# 三、发送请求
# ===========================================================================

def call_model(messages, max_tokens):
    """发送一次请求，返回 (服务端返回的字典, 客户端耗时秒数)。"""
    generation = CONFIG["generation"]
    body = {
        "model": "local",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": generation["temperature"],
        "top_p": generation["top_p"],
        "seed": generation["seed"],
        "chat_template_kwargs": {"enable_thinking": generation["enable_thinking"]},
    }

    request = urllib.request.Request(
        SERVER_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    started = time.time()
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        raw = response.read().decode("utf-8")
    elapsed = time.time() - started

    return json.loads(raw), elapsed


def run_one_task(task, run_id, round_no, index):
    """跑一条任务，返回一条完整记录（成功或失败都返回）。"""
    messages = build_messages(task)

    record = {
        "run_id": run_id,
        "request_id": f"{run_id}-{task['id']}-r{round_no}",
        "round": round_no,
        "seq": index,
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
        "prompt_tokens": None,
        "completion_tokens": None,
        "cached_tokens": None,
        "client_seconds": None,
        "server_timings": None,
        "started_at": datetime.now().isoformat(timespec="seconds"),
    }

    try:
        payload, elapsed = call_model(messages, task["max_tokens"])
        choice = payload["choices"][0]
        usage = payload.get("usage", {})

        record["status"] = "ok"
        record["answer"] = choice["message"]["content"]
        record["finish_reason"] = choice.get("finish_reason")
        record["prompt_tokens"] = usage.get("prompt_tokens")
        record["completion_tokens"] = usage.get("completion_tokens")
        record["cached_tokens"] = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
        record["client_seconds"] = round(elapsed, 3)
        record["server_timings"] = payload.get("timings")
    except urllib.error.HTTPError as exc:
        record["status"] = "http_error"
        record["error"] = exc.read().decode("utf-8", "replace")[:500]
    except Exception as exc:                                  # noqa: BLE001
        record["status"] = "failed"
        record["error"] = f"{type(exc).__name__}: {exc}"

    return record


# ===========================================================================
# 四、跑完整负载
# ===========================================================================

def run_workload(rounds=1):
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = RUNS_DIR / f"{run_id}.jsonl"

    print(f"运行编号：{run_id}")
    print(f"记录文件：{out_path}")
    print(f"轮次：{rounds}　并发：1")
    print("=" * 78)

    records = []
    with out_path.open("w", encoding="utf-8") as out:
        for round_no in range(1, rounds + 1):
            for index, task in enumerate(CONFIG["tasks"], start=1):
                record = run_one_task(task, run_id, round_no, index)
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                out.flush()                       # 立刻落盘，中途出错也不丢
                records.append(record)

                if record["status"] == "ok":
                    print(f"  [轮{round_no} {index:>2}/10] {task['id']}  "
                          f"输出 {record['completion_tokens']:>4} token  "
                          f"{record['client_seconds']:>7.2f} 秒  "
                          f"{record['finish_reason']}")
                else:
                    print(f"  [轮{round_no} {index:>2}/10] {task['id']}  "
                          f"!! {record['status']}：{str(record['error'])[:80]}")

    print_summary(records, run_id, out_path)
    return records


def print_summary(records, run_id, out_path):
    ok = [r for r in records if r["status"] == "ok"]
    failed = [r for r in records if r["status"] != "ok"]

    print()
    print("=" * 78)
    print(f"汇总　运行编号 {run_id}")
    print("-" * 78)
    print(f"{'任务':<6}{'状态':<10}{'输入token':>10}{'输出token':>11}{'耗时(秒)':>10}{'输出字符':>10}")
    for r in records:
        answer_len = len(r["answer"]) if r["answer"] else 0
        print(f"{r['task_id']:<6}{r['status']:<10}"
              f"{str(r['prompt_tokens'] or '-'):>10}"
              f"{str(r['completion_tokens'] or '-'):>11}"
              f"{str(r['client_seconds'] or '-'):>10}"
              f"{answer_len:>10}")

    print("-" * 78)
    total_sec = sum(r["client_seconds"] or 0 for r in ok)
    total_out = sum(r["completion_tokens"] or 0 for r in ok)
    if total_sec:
        print(f"成功 {len(ok)} / 失败 {len(failed)}　总输出 {total_out} token　"
              f"总耗时 {total_sec:.1f} 秒　平均 {total_out / total_sec:.1f} token/秒")
    else:
        print(f"成功 {len(ok)} / 失败 {len(failed)}　（没有成功记录）")
    print(f"原始记录：{out_path}")


# ===========================================================================
# 入口
# ===========================================================================

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry"

    if mode == "dry":
        print_task_list()
        dry_run(["P01", "D01"])
    elif mode == "run":
        run_workload(rounds=1)
    else:
        print("用法：python3 src/runner.py [run]")
        print("  不带参数  只拼装不发送（输入核查）")
        print("  run       真正跑一遍负载")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
