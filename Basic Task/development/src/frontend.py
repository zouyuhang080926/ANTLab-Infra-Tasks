#!/usr/bin/env python3
"""
frontend.py —— 本地推理服务的展示界面

设计原则：
  · 只用 Python 标准库，不需要 npm install，评委拿到仓库就能跑；
  · 数据来源只有两个：llama-server 的 HTTP 接口，以及 results/runs/ 下的记录文件；
  · 前端只负责显示，统计一律在服务端算好再送过去，避免两处算法不一致。

用法：
    python3 src/frontend.py            # 默认端口 8000
    python3 src/frontend.py 8080       # 指定端口

浏览器打开： http://localhost:8000
"""

import json
import glob
import os
import subprocess
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

DEV_DIR = Path(__file__).resolve().parent.parent
RUNS_DIR = DEV_DIR / "results" / "runs"
WEB_DIR = Path(__file__).resolve().parent / "web"
CONFIG_PATH = DEV_DIR / "configs" / "workload.json"

LLAMA_BASE = "http://127.0.0.1:8888"


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
def percentile(values, p):
    if not values:
        return None
    data = sorted(values)
    k = (len(data) - 1) * p
    low = int(k)
    high = min(low + 1, len(data) - 1)
    if low == high:
        return data[low]
    return data[low] + (data[high] - data[low]) * (k - low)


def fetch_llama(path, timeout=5):
    try:
        with urllib.request.urlopen(LLAMA_BASE + path, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:                                  # noqa: BLE001
        return {"error": "%s: %s" % (type(exc).__name__, exc)}


def fetch_text(path, timeout=5, limit=4000):
    """取纯文本（用于 /metrics：它返回的是 Prometheus 文本格式，不是 JSON）。"""
    try:
        with urllib.request.urlopen(LLAMA_BASE + path, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace")[:limit]
    except Exception as exc:                                  # noqa: BLE001
        return "无法获取：%s: %s" % (type(exc).__name__, exc)


def gpu_snapshot():
    query = "name,temperature.gpu,clocks.current.graphics,power.draw,memory.used,memory.total"
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=" + query, "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10, check=True).stdout.strip()
        parts = [p.strip() for p in out.split(",")]
        keys = ["name", "temperature_c", "clock_mhz", "power_w", "vram_used_mib", "vram_total_mib"]
        return dict(zip(keys, parts))
    except Exception as exc:                                  # noqa: BLE001
        return {"error": str(exc)}


def summarize(records):
    """把一批记录压成汇总指标。统计口径与 configs/metrics.md 一致。"""
    ok = [r for r in records if r["status"] == "ok"]
    bad = [r for r in records if r["status"] != "ok"]

    ttfts = [r["ttft_seconds"] for r in ok if r.get("ttft_seconds")]
    totals = [r["client_seconds"] for r in ok if r.get("client_seconds")]
    tpots = [r["tpot_seconds"] for r in ok if r.get("tpot_seconds")]
    out_tokens = sum(r.get("completion_tokens") or 0 for r in ok)

    starts = [r["started_epoch"] for r in records if r.get("started_epoch")]
    ends = [r["finished_epoch"] for r in records if r.get("finished_epoch")]
    wall = (max(ends) - min(starts)) if starts and ends else None

    return {
        "total": len(records),
        "success": len(ok),
        "failed": len(bad),
        "ttft_median": percentile(ttfts, 0.5),
        "ttft_p95": percentile(ttfts, 0.95),
        "total_median": percentile(totals, 0.5),
        "total_p95": percentile(totals, 0.95),
        "tpot_median": percentile(tpots, 0.5),
        "output_tokens": out_tokens,
        "wall_seconds": wall,
        "throughput": (out_tokens / wall) if wall else None,
        "cached_tokens": sum(r.get("cached_tokens") or 0 for r in ok),
        "truncated": sum(1 for r in ok if r.get("finish_reason") == "length"),
    }


def load_run(run_id):
    path = RUNS_DIR / (run_id + ".jsonl")
    if not path.exists():
        return None
    records = [json.loads(line) for line in path.open(encoding="utf-8")]
    env = None
    env_path = RUNS_DIR / (run_id + ".env.json")
    if env_path.exists():
        env = json.loads(env_path.read_text(encoding="utf-8"))
    return {"run_id": run_id, "records": records, "summary": summarize(records),
            "env": env}


def list_runs():
    out = []
    for path in sorted(glob.glob(str(RUNS_DIR / "*.jsonl")), key=os.path.getmtime, reverse=True):
        run_id = Path(path).stem
        records = [json.loads(line) for line in open(path, encoding="utf-8")]
        first = records[0] if records else {}
        out.append({
            "run_id": run_id,
            "mtime": os.path.getmtime(path),
            "rounds": max((r.get("round") or 1) for r in records) if records else 0,
            "concurrency": first.get("concurrency", 1),
            "records": len(records),
            "summary": summarize(records),
        })
    return out


def per_task(records):
    """按任务聚合，供逐任务表格使用。"""
    tasks = {}
    for r in records:
        key = r["task_id"]
        item = tasks.setdefault(key, {
            "task_id": key, "title": r.get("task_title", ""), "type": r.get("task_type", ""),
            "max_tokens": r.get("max_tokens"), "runs": 0, "ok": 0,
            "ttft": [], "total": [], "out_tokens": 0, "cached": 0, "reasons": set(),
        })
        item["runs"] += 1
        if r["status"] == "ok":
            item["ok"] += 1
            if r.get("ttft_seconds"):
                item["ttft"].append(r["ttft_seconds"])
            if r.get("client_seconds"):
                item["total"].append(r["client_seconds"])
            item["out_tokens"] += r.get("completion_tokens") or 0
            item["cached"] += r.get("cached_tokens") or 0
            item["reasons"].add(r.get("finish_reason") or "-")

    rows = []
    for item in tasks.values():
        rows.append({
            "task_id": item["task_id"], "title": item["title"], "type": item["type"],
            "max_tokens": item["max_tokens"], "runs": item["runs"], "ok": item["ok"],
            "ttft_median": percentile(item["ttft"], 0.5),
            "total_median": percentile(item["total"], 0.5),
            "out_tokens": item["out_tokens"], "cached": item["cached"],
            "finish": "/".join(sorted(item["reasons"])),
        })
    return rows


# ---------------------------------------------------------------------------
# HTTP 处理
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):        # 静音：只保留自己的日志
        pass

    def _send(self, code, body, content_type="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path, query = parsed.path, parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            html = (WEB_DIR / "index.html")
            if not html.exists():
                return self._send(500, {"error": "找不到 web/index.html"})
            return self._send(200, html.read_text(encoding="utf-8"),
                              "text/html; charset=utf-8")

        if path == "/api/status":
            return self._send(200, {
                "health": fetch_llama("/health"),
                "metrics_text": fetch_text("/metrics"),
                "gpu": gpu_snapshot(),
                "llama_base": LLAMA_BASE,
            })

        if path == "/api/runs":
            return self._send(200, {"runs": list_runs()})

        if path == "/api/config":
            if CONFIG_PATH.exists():
                return self._send(200, json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
            return self._send(404, {"error": "找不到 workload.json"})

        if path.startswith("/api/run/"):
            run_id = path[len("/api/run/"):]
            data = load_run(run_id)
            if not data:
                return self._send(404, {"error": "找不到运行 " + run_id})
            data["per_task"] = per_task(data["records"])
            return self._send(200, data)

        if path == "/api/compare":
            a, b = query.get("a", [None])[0], query.get("b", [None])[0]
            ra, rb = load_run(a) if a else None, load_run(b) if b else None
            if not ra or not rb:
                return self._send(400, {"error": "需要 a 与 b 两个运行编号"})
            return self._send(200, {
                "a": {"run_id": a, "summary": ra["summary"], "per_task": per_task(ra["records"])},
                "b": {"run_id": b, "summary": rb["summary"], "per_task": per_task(rb["records"])},
            })

        self._send(404, {"error": "未知路径 " + path})


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print("=" * 60)
    print(" 本地推理服务 · 展示界面")
    print(" 地址：  http://localhost:%d" % port)
    print(" 推理服务：%s" % LLAMA_BASE)
    print(" 记录目录：%s" % RUNS_DIR)
    print(" Ctrl+C 退出")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已退出。")


if __name__ == "__main__":
    main()
