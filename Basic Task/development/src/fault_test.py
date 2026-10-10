#!/usr/bin/env python3
"""
fault_test.py —— 服务退出与恢复实验

做三件事：
  1. 在负载运行途中，**直接把服务进程杀掉**（模拟真实崩溃，不是先停再改配置）；
  2. 监控线程检测到不可用后自动重启并确认就绪，全程记录时间线；
  3. 记录每个受影响请求的最终状态，并在恢复后验证推理功能真的回来了。

三类请求的处理方式（本项目定义）：

| 类别       | 定义                       | 处理方式                                   |
|------------|----------------------------|--------------------------------------------|
| 等待中     | 尚未发出的请求             | 等服务恢复后再发，**不计为失败、不消耗重试** |
| 已发送     | 已发出但未收到完整响应     | 计入一次尝试，按上限重试                    |
| 失败       | 重试次数用尽的请求         | 标记为 failed，**计入分母**                 |

计数口径：同一 request_id 无论重试几次，**只产生一条最终记录**（attempts 字段记录重试次数），
避免重试导致重复计数。

用法：
    python3 src/fault_test.py
"""

import json
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

DEV_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DEV_DIR / "src"))
from supervisor import Supervisor                                  # noqa: E402

CONFIG = json.loads((DEV_DIR / "configs" / "workload.json").read_text(encoding="utf-8"))
INPUT_DIR = DEV_DIR.parent / "提示词与输入文档" / "输入文档"
OUT_DIR = DEV_DIR / "results" / "fault_test"

PORT = 8888
URL = "http://127.0.0.1:%d/v1/chat/completions" % PORT
MAX_RETRIES = 3          # 已发送请求的最大重试次数
RETRY_WAIT = 5           # 每次重试前等待秒数
WAIT_BUDGET = 20         # 单个请求等待服务恢复的**总**预算（秒）
                         # 注意是"每个请求一个总预算"，不是"每次尝试各等一份"，
                         # 否则服务长期不可用时单个请求会无限拖长。
KILL_AFTER = 3           # 第几条任务开始后注入故障
KILL_DELAY = 3           # 在第几条任务**执行途中**延迟几秒再注入（覆盖"已发送请求"路径）

# 是否让监控线程自动重启。关掉时用于验证"重试次数耗尽"的失败路径。
AUTO_RESTART = "--no-restart" not in sys.argv

sup = Supervisor(port=PORT)
LOG_LOCK = threading.Lock()
TIMELINE = []


def record(kind, detail=""):
    with LOG_LOCK:
        item = {"time": datetime.now().isoformat(timespec="milliseconds"),
                "epoch": round(time.time(), 3), "kind": kind, "detail": detail}
        TIMELINE.append(item)
        print("      · %-18s %s" % (kind, detail))
        return item


# ---------------------------------------------------------------------------
def build_messages(task):
    if task["file"]:
        content = (INPUT_DIR / task["file"]).read_text(encoding="utf-8")
        user = CONFIG["user_template"].format(
            file_name=task["file"], file_sha256=task["file_sha256"],
            file_content=content, prompt=task["prompt"])
    else:
        user = CONFIG["user_template_no_file"].format(prompt=task["prompt"])
    return [{"role": "system", "content": CONFIG["system_message"]},
            {"role": "user", "content": user}]


def call(messages, max_tokens):
    g = CONFIG["generation"]
    body = {"model": "local", "messages": messages, "max_tokens": max_tokens,
            "temperature": g["temperature"], "top_p": g["top_p"], "seed": g["seed"],
            "chat_template_kwargs": {"enable_thinking": g["enable_thinking"]}}
    req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=600) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload, time.monotonic() - started


# ---------------------------------------------------------------------------
class Watcher(threading.Thread):
    """健康监控线程：发现服务不可用就自动重启，并记录时间线。"""

    def __init__(self):
        super().__init__(daemon=True)
        self.stop_flag = threading.Event()
        self.detected_at = None
        self.recovered_at = None

    def run(self):
        while not self.stop_flag.is_set():
            alive, detail = sup.health(timeout=3)
            if not alive:
                if self.detected_at is None:
                    self.detected_at = time.monotonic()
                    record("异常检出", "健康检查失败：%s" % detail[:60])
                if not AUTO_RESTART:
                    record("保持停机", "本次实验关闭自动重启，用于验证重试耗尽路径")
                    time.sleep(1)
                    continue
                # 等服务真的退出（避免与故障注入的 kill 抢时序）
                time.sleep(1)
                if sup.restart():
                    self.recovered_at = time.monotonic()
                    record("恢复完成", "重启并就绪，用时 %.1f 秒"
                           % (self.recovered_at - self.detected_at))
                else:
                    record("恢复失败", "重启后仍未就绪")
                continue
            time.sleep(1)


def inject_fault():
    """模拟真实崩溃：直接杀掉进程。"""
    record("注入故障", "直接终止服务进程")
    sup.stop()


def inject_fault_later(delay):
    """延迟若干秒后在**请求执行途中**注入故障。

    这样才会出现"已发送但未收到完整响应"的请求，
    用于验证该路径下的重试与去重行为。
    """
    time.sleep(delay)
    inject_fault()


# ---------------------------------------------------------------------------
def run_task_with_retry(task, index, run_id):
    """跑一条任务，带重试。返回一条最终记录（重试不产生重复记录）。"""
    request_id = "%s-%s" % (run_id, task["id"])
    # 注意：这里的变量不能叫 record，否则会遮蔽上面的 record() 函数
    entry = {
        "run_id": run_id, "request_id": request_id, "seq": index,
        "task_id": task["id"], "task_title": task["title"],
        "status": "pending", "attempts": 0, "attempt_log": [],
        "final_status": None, "answer_chars": None,
        "client_seconds": None, "error": None,
    }

    attempt = 0
    waited_total = 0.0
    while attempt <= MAX_RETRIES:
        # 发出前先看服务是否可用：不可用属于"等待中"，不消耗重试次数
        if not sup.is_alive() and waited_total < WAIT_BUDGET:
            record("请求等待", "%s 服务不可用，等待恢复后再发" % task["id"])
            while not sup.is_alive() and waited_total < WAIT_BUDGET:
                time.sleep(1)
                waited_total += 1
            record("等待结束", "%s 累计等待 %.0f 秒，服务%s"
                   % (task["id"], waited_total, "已恢复" if sup.is_alive() else "仍不可用"))

        # 等待预算用尽且服务仍不可用：请求从未发出，标记失败且不再重试
        if not sup.is_alive():
            entry["final_status"] = "failed"
            entry["status"] = "never_sent"
            give_up = "服务不可用，等待 %.0f 秒后仍未恢复，剩余请求不再发出" % waited_total
            # 保留此前的失败原因，避免被后来这句覆盖掉
            entry["error"] = (give_up + "；此前尝试失败：" + entry["error"]) \
                if entry.get("error") else give_up
            entry["attempt_log"].append(
                {"attempt": attempt, "result": "not_sent", "error": give_up})
            record("请求放弃", "%s %s" % (task["id"], give_up))
            return entry

        attempt += 1
        entry["attempts"] = attempt
        entry["status"] = "in_flight"
        try:
            payload, elapsed = call(build_messages(task), task["max_tokens"])
            entry["final_status"] = "ok"
            entry["client_seconds"] = round(elapsed, 3)
            entry["answer_chars"] = len(payload["choices"][0]["message"]["content"])
            entry["attempt_log"].append({"attempt": attempt, "result": "ok"})
            return entry
        except Exception as exc:                              # noqa: BLE001
            msg = "%s: %s" % (type(exc).__name__, str(exc)[:120])
            entry["attempt_log"].append({"attempt": attempt, "result": "error", "error": msg})
            entry["error"] = msg
            record("请求失败", "%s 第 %d 次尝试：%s" % (task["id"], attempt, msg[:70]))
            if attempt <= MAX_RETRIES:
                time.sleep(RETRY_WAIT)

    entry["final_status"] = "failed"
    return entry


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 72)
    print("服务退出与恢复实验　运行编号 %s" % run_id)
    print("自动重启：%s" % ("开启" if AUTO_RESTART else "关闭（验证失败路径）"))
    print("=" * 72)

    # 1) 确保服务可用
    if not sup.ensure_running():
        print("服务无法启动，实验中止")
        return 1

    # 2) 预热
    print("\n预热……")
    for _ in range(2):
        try:
            call(build_messages(CONFIG["tasks"][0]), 64)
        except Exception:                                     # noqa: BLE001
            pass

    # 3) 启动监控线程
    watcher = Watcher()
    watcher.start()
    record("监控启动", "每秒检测一次健康状态")

    # 4) 跑负载，途中注入故障
    print("\n开始运行负载（将在第 %d 条任务后注入故障）\n" % KILL_AFTER)
    records = []
    fault_done = False
    for index, task in enumerate(CONFIG["tasks"], start=1):
        print("  [%2d/10] %s" % (index, task["id"]))
        if index == KILL_AFTER + 1 and not fault_done:
            threading.Thread(target=inject_fault_later, args=(KILL_DELAY,),
                             daemon=True).start()
            record("计划注入", "%d 秒后终止服务（此时该请求应处于已发送状态）" % KILL_DELAY)
            fault_done = True
        rec = run_task_with_retry(task, index, run_id)
        records.append(rec)
        print("         → %s（尝试 %d 次）\n" % (rec["final_status"], rec["attempts"]))

    # 关闭自动重启的实验里，负载跑完后手动恢复一次，再验证可用性
    if not AUTO_RESTART:
        record("手动恢复", "负载结束，执行一次恢复")
        sup.ensure_running()

    # 5) 恢复后验证：独立发一条新请求
    print("恢复后验证……")
    verify_ok, verify_detail = False, ""
    try:
        payload, elapsed = call(build_messages(CONFIG["tasks"][0]), 64)
        verify_ok = bool(payload["choices"][0]["message"]["content"])
        verify_detail = "收到回答 %d 字符，用时 %.2f 秒" % (
            len(payload["choices"][0]["message"]["content"]), elapsed)
    except Exception as exc:                                  # noqa: BLE001
        verify_detail = "%s: %s" % (type(exc).__name__, exc)
    record("恢复验证", ("成功：" if verify_ok else "失败：") + verify_detail)

    watcher.stop_flag.set()
    time.sleep(1.5)

    # 6) 汇总
    ok = [r for r in records if r["final_status"] == "ok"]
    recovered = [r for r in ok if r["attempts"] > 1]
    failed = [r for r in records if r["final_status"] == "failed"]

    print()
    print("=" * 72)
    print("汇总")
    print("=" * 72)
    print("  请求总数（按 request_id 去重）：%d" % len(records))
    print("  成功：%d　其中经重试恢复：%d" % (len(ok), len(recovered)))
    print("  失败：%d" % len(failed))
    print("  总尝试次数：%d　（其中重试 %d 次；未发出的请求不计尝试）"
          % (sum(r["attempts"] for r in records),
             sum(max(0, r["attempts"] - 1) for r in records)))
    if watcher.detected_at and watcher.recovered_at:
        print("  异常检出到恢复完成：%.1f 秒"
              % (watcher.recovered_at - watcher.detected_at))
    elif watcher.detected_at:
        print("  异常检出到恢复完成：本次关闭自动重启，未自动恢复")
    print("  未发出的请求（等待超时）：%d"
          % sum(1 for r in records if r["status"] == "never_sent"))
    print("  恢复后独立验证：%s" % ("通过" if verify_ok else "未通过"))

    print()
    print("  受影响请求（尝试次数 > 1 或最终失败）：")
    for r in records:
        if r["attempts"] > 1 or r["final_status"] != "ok":
            print("    %-5s 最终=%-7s 尝试 %d 次  %s"
                  % (r["task_id"], r["final_status"], r["attempts"],
                     (r["error"] or "")[:60]))

    # 7) 落盘
    (OUT_DIR / (run_id + ".jsonl")).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8")
    (OUT_DIR / (run_id + "_timeline.json")).write_text(
        json.dumps(TIMELINE, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print()
    print("  记录：%s" % (OUT_DIR / (run_id + ".jsonl")))
    print("  时间线：%s" % (OUT_DIR / (run_id + "_timeline.json")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
