#!/usr/bin/env python3
"""
replay.py —— 按参考请求序列回放，比较三种调度策略

流程：
    按 arrival_offset_ms 把 16 条请求投入队列（到达顺序固定不变），
    调度器决定处理顺序，单工作线程逐条发往推理服务，全程记录。

为什么单工作线程：
    调度考察的是"排队与顺序"。若并发处理，等待时间会被并发度掩盖，
    无法归因于调度策略本身。并发度固定为 1，三种策略完全一致。

输出预算：
    参考序列给出的 suggested_output_budget_tokens 是起点，本实验
    统一取其与 1024 的较小值并固定，以控制单轮时长；该调整会记入配置。

用法：
    python3 src/replay.py fifo|priority|priority_cache [轮数]
    python3 src/replay.py all 3          # 三种策略各跑 3 轮
"""

import json
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

DEV_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DEV_DIR / "src"))
from scheduler import Scheduler                                   # noqa: E402
from supervisor import Supervisor                                 # noqa: E402

# 每轮开始前重启服务以清空 KV 缓存。
# 为什么必须做：若不清空，上一轮留下的前缀会继续被命中，
# 所有策略的 cached_tokens 都被"残留缓存"主导，测不出调度的影响。
SUP = Supervisor(port=8888, extra_args=["-ngl", "99", "-c", "16384",
                                        "-cram", "0", "--metrics"])

ADV_DIR = DEV_DIR.parent.parent / "Advanced Task" / "参考测试（仅作参考）"
SEQ_PATH = ADV_DIR / "参考请求序列.jsonl"
PROMPT_DOC = ADV_DIR / "测试提示词.md"
INPUT_DIR = ADV_DIR / "输入文档"
OUT_DIR = DEV_DIR / "results" / "advanced"

SERVER_URL = "http://127.0.0.1:8888/v1/chat/completions"
TIMEOUT = 600
BUDGET_CAP = 1024                 # 输出预算上限，见文件头说明

SYSTEM_MESSAGE = (
    "你为小型工作室处理办公文档和编程任务。按照任务要求输出，"
    "将资料事实、待确认信息与建议分别表述。以本次提供的文档版本为依据，"
    "代码任务提供可检查的实现。"
)
USER_TEMPLATE = "【资料】\n{file_name}\n-----\n{content}\n-----\n\n【任务】\n{prompt}"
USER_TEMPLATE_NO_FILE = "【任务】\n{prompt}"

BLOCK = re.compile(r"^###\s+(T\d{2})｜(.+?)\s*$", re.M)
ASSOC = re.compile(r"关联文件：`([^`]+)`")


# ---------------------------------------------------------------------------
def parse_prompts():
    """从参考测试提示词里抽出 T01~T08 的提示词与关联文件。"""
    text = PROMPT_DOC.read_text(encoding="utf-8")
    parts = BLOCK.split(text)
    # split 结果形如 [前言, "T01", 标题1, 正文1, "T02", 标题2, 正文2, ...]
    out = {}
    for i in range(1, len(parts), 3):
        tid, title, body = parts[i], parts[i + 1], parts[i + 2]
        m = ASSOC.search(body)
        fname = Path(m.group(1)).name if m else None
        prompt = ASSOC.sub("", body).strip()
        out[tid] = {"title": title.strip(), "file": fname, "prompt": prompt}
    return out


def build_messages(spec, prompt_map):
    info = prompt_map[spec["prompt_id"]]
    if info["file"]:
        content = (INPUT_DIR / info["file"]).read_text(encoding="utf-8")
        user = USER_TEMPLATE.format(file_name=info["file"], content=content,
                                    prompt=info["prompt"])
    else:
        user = USER_TEMPLATE_NO_FILE.format(prompt=info["prompt"])
    return [{"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": user}]


def call_model(messages, max_tokens):
    body = {"model": "local", "messages": messages, "max_tokens": max_tokens,
            "temperature": 0, "top_p": 1.0, "seed": 0,
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(SERVER_URL, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload, time.monotonic() - t0


# ---------------------------------------------------------------------------
def run_one_round(policy, round_no, prompt_map, sequence, results):
    sched = Scheduler(policy=policy)
    run_id = "%s_r%d_%s" % (datetime.now().strftime("%Y%m%d_%H%M%S"),
                            round_no, policy)
    pending = list(sequence)
    # 清空缓存：从冷启动状态开始，三种策略的起点完全一致
    if not SUP.restart():
        raise RuntimeError("服务重启失败，无法保证缓存状态一致")
    t_start = time.monotonic()
    lock = threading.Lock()

    def feeder():
        """按到达时间把请求投入队列。"""
        for spec in pending:
            target = t_start + spec["arrival_offset_ms"] / 1000.0
            wait = target - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            job = dict(spec)
            job["arrival_actual_epoch"] = time.time()
            job["arrival_planned_ms"] = spec["arrival_offset_ms"]
            with lock:
                sched.submit(job)

    def worker():
        """单工作线程：按调度策略逐条处理。"""
        while len(results) < len(sequence):
            job = sched.pick_next()
            if job is None:
                time.sleep(0.05)
                continue
            job["dispatched_epoch"] = time.time()
            rec = {
                "run_id": run_id, "policy": policy, "round": round_no,
                "request_id": job["request_id"], "session_id": job["session_id"],
                "task_type": job["task_type"], "interaction_mode": job["interaction_mode"],
                "prompt_id": job["prompt_id"],
                "arrival_planned_ms": job["arrival_planned_ms"],
                "arrival_actual_ms": round((job["arrival_actual_epoch"] - t_start) * 1000, 1),
                "waiting_seconds": round(job["dispatched_epoch"] - job["enqueued_epoch"], 3),
                "deadline_ms": job["deadline_after_arrival_ms"],
                "budget": min(job["suggested_output_budget_tokens"], BUDGET_CAP),
                "status": None, "error": None,
                "prompt_tokens": None, "completion_tokens": None, "cached_tokens": None,
                "service_seconds": None, "end_to_end_seconds": None,
                "met_deadline": None, "finish_reason": None,
            }
            try:
                payload, elapsed = call_model(build_messages(job, prompt_map), rec["budget"])
                usage = payload.get("usage") or {}
                choice = payload["choices"][0]
                rec["status"] = "ok"
                rec["prompt_tokens"] = usage.get("prompt_tokens")
                rec["completion_tokens"] = usage.get("completion_tokens")
                rec["cached_tokens"] = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
                rec["finish_reason"] = choice.get("finish_reason")
                rec["service_seconds"] = round(elapsed, 3)
            except Exception as exc:                          # noqa: BLE001
                rec["status"] = "failed"
                rec["error"] = "%s: %s" % (type(exc).__name__, str(exc)[:120])

            finished = time.time()
            rec["end_to_end_seconds"] = round(finished - job["arrival_actual_epoch"], 3)
            if rec["status"] == "ok":
                rec["met_deadline"] = rec["end_to_end_seconds"] * 1000 <= rec["deadline_ms"]
            sched.mark_done(job)

            with lock:
                results.append(rec)
                print("    %-5s %-11s 等待 %6.2fs 服务 %6.2fs 端到端 %6.2fs  %s%s"
                      % (rec["request_id"], rec["interaction_mode"],
                         rec["waiting_seconds"], rec["service_seconds"] or 0,
                         rec["end_to_end_seconds"],
                         "按期" if rec["met_deadline"] else "超期",
                         "" if rec["status"] == "ok" else "  !! " + rec["error"]))

    threads = [threading.Thread(target=feeder, daemon=True),
               threading.Thread(target=worker, daemon=True)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return sched, run_id


def summarize(records):
    ok = [r for r in records if r["status"] == "ok"]
    inter = [r for r in ok if r["interaction_mode"] == "interactive"]
    batch = [r for r in ok if r["interaction_mode"] == "batch"]

    def med(vals):
        vals = sorted(vals)
        return vals[len(vals) // 2] if vals else None

    return {
        "total": len(records), "success": len(ok),
        "interactive_wait_median": med([r["waiting_seconds"] for r in inter]),
        "batch_wait_median": med([r["waiting_seconds"] for r in batch]),
        "interactive_e2e_median": med([r["end_to_end_seconds"] for r in inter]),
        "batch_e2e_median": med([r["end_to_end_seconds"] for r in batch]),
        "batch_wait_max": max([r["waiting_seconds"] for r in batch]) if batch else None,
        "deadline_rate": (sum(1 for r in ok if r["met_deadline"]) / len(ok)) if ok else None,
        "interactive_deadline_rate": (sum(1 for r in inter if r["met_deadline"]) / len(inter)) if inter else None,
        "batch_deadline_rate": (sum(1 for r in batch if r["met_deadline"]) / len(batch)) if batch else None,
        "cached_tokens": sum(r["cached_tokens"] or 0 for r in ok),
        "prompt_tokens": sum(r["prompt_tokens"] or 0 for r in ok),
    }


def main():
    policy = sys.argv[1] if len(sys.argv) > 1 else "fifo"
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    policies = ["fifo", "priority", "priority_cache"] if policy == "all" else [policy]

    prompt_map = parse_prompts()
    sequence = [json.loads(l) for l in SEQ_PATH.open(encoding="utf-8") if l.strip()]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("提示词：%d 条　请求序列：%d 条" % (len(prompt_map), len(sequence)))
    print("策略：%s　轮次：%d" % ("、".join(policies), rounds))
    print("=" * 84)

    everything = []
    for pol in policies:
        for rnd in range(1, rounds + 1):
            print("\n>>> 策略 %s　第 %d 轮" % (pol, rnd))
            results = []
            sched, run_id = run_one_round(pol, rnd, prompt_map, sequence, results)
            s = summarize(results)
            out = OUT_DIR / (run_id + ".jsonl")
            out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in results) + "\n",
                           encoding="utf-8")
            (OUT_DIR / (run_id + "_decisions.json")).write_text(
                json.dumps(sched.log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            print("    成功 %d/%d　按期率 %.0f%%　"
                  "交互等待中位 %.1fs　后台等待中位 %.1fs　后台最大等待 %.1fs　缓存命中 %d"
                  % (s["success"], s["total"],
                     (s["deadline_rate"] or 0) * 100,
                     s["interactive_wait_median"] or 0,
                     s["batch_wait_median"] or 0,
                     s["batch_wait_max"] or 0,
                     s["cached_tokens"]))
            everything.append({"policy": pol, "round": rnd, "run_id": run_id, "summary": s})

    (OUT_DIR / "summary.json").write_text(
        json.dumps(everything, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\n汇总：%s" % (OUT_DIR / "summary.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
