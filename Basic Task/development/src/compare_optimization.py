#!/usr/bin/env python3
"""
compare_optimization.py —— 汇总各配置的优化对比

读取 results/optimization/ 下每个配置对应的运行编号，
再回到 results/runs/ 里取原始记录，生成对比表。

用法：
    python3 src/compare_optimization.py
"""

import glob
import json
import os
import re
import sys
from pathlib import Path

DEV_DIR = Path(__file__).resolve().parent.parent
OPT_DIR = DEV_DIR / "results" / "optimization"
RUNS_DIR = DEV_DIR / "results" / "runs"


def percentile(values, p):
    if not values:
        return None
    data = sorted(values)
    k = (len(data) - 1) * p
    low = int(k)
    high = min(low + 1, len(data) - 1)
    return data[low] if low == high else data[low] + (data[high] - data[low]) * (k - low)


def summarize(records):
    ok = [r for r in records if r["status"] == "ok"]
    ttfts = [r["ttft_seconds"] for r in ok if r.get("ttft_seconds")]
    totals = [r["client_seconds"] for r in ok if r.get("client_seconds")]
    out_tokens = sum(r.get("completion_tokens") or 0 for r in ok)
    cached = sum(r.get("cached_tokens") or 0 for r in ok)
    prompt = sum(r.get("prompt_tokens") or 0 for r in ok)
    starts = [r["started_epoch"] for r in records if r.get("started_epoch")]
    ends = [r["finished_epoch"] for r in records if r.get("finished_epoch")]
    wall = (max(ends) - min(starts)) if starts and ends else 0
    return {
        "success": len(ok), "total": len(records),
        "truncated": sum(1 for r in ok if r.get("finish_reason") == "length"),
        "ttft_median": percentile(ttfts, 0.5), "ttft_p95": percentile(ttfts, 0.95),
        "total_median": percentile(totals, 0.5),
        "out_tokens": out_tokens, "wall": wall,
        "throughput": (out_tokens / wall) if wall else None,
        "cached": cached, "prompt": prompt,
        "cache_rate": (cached / prompt) if prompt else None,
    }


def main():
    txts = sorted(glob.glob(str(OPT_DIR / "*.txt")))
    if not txts:
        sys.exit("找不到结果文件，先跑 work/optimize_experiments.sh")

    rows = []
    for path in txts:
        name = Path(path).stem
        text = Path(path).read_text(encoding="utf-8")
        m = re.search(r"运行编号[：:]\s*(\S+)", text)
        if not m:
            print("跳过 %s：里面没有运行编号" % name)
            continue
        run_id = m.group(1)
        jl = RUNS_DIR / (run_id + ".jsonl")
        if not jl.exists():
            print("跳过 %s：找不到 %s" % (name, jl.name))
            continue
        records = [json.loads(l) for l in jl.open(encoding="utf-8")]
        rows.append((name, run_id, summarize(records)))

    if not rows:
        sys.exit("没有可汇总的数据")

    base = rows[0][2]
    print("=" * 88)
    print("配置级优化对比（负载 v5，单并发 3 轮，同一台机器、插电、预热后）")
    print("=" * 88)
    print()
    print("%-14s%-16s%8s%8s%9s%9s%10s%9s" % (
        "配置", "运行编号", "成功", "截断", "TTFT中位", "吞吐", "输出token", "缓存命中率"))
    print("-" * 88)
    for name, run_id, s in rows:
        print("%-14s%-16s%8s%8s%9s%9s%10s%9s" % (
            name, run_id,
            "%d/%d" % (s["success"], s["total"]),
            s["truncated"],
            "--" if s["ttft_median"] is None else "%.2fs" % s["ttft_median"],
            "--" if s["throughput"] is None else "%.1f t/s" % s["throughput"],
            s["out_tokens"],
            "--" if s["cache_rate"] is None else "%.1f%%" % (s["cache_rate"] * 100),
        ))

    print()
    print("相对基线（%s）的变化：" % rows[0][0])
    print("-" * 88)
    for name, run_id, s in rows[1:]:
        parts = []
        if base["throughput"] and s["throughput"]:
            parts.append("吞吐 %+.1f%%" % ((s["throughput"] / base["throughput"] - 1) * 100))
        if base["ttft_median"] and s["ttft_median"]:
            parts.append("TTFT中位 %+.1f%%" % ((s["ttft_median"] / base["ttft_median"] - 1) * 100))
        if base["wall"] and s["wall"]:
            parts.append("墙钟 %+.1f%%" % ((s["wall"] / base["wall"] - 1) * 100))
        print("  %-14s %s" % (name, "　".join(parts)))

    print()
    print("注：各项均使用同一份负载（v5）与同一组参数，仅改动一项配置。")

    out = OPT_DIR / "对比汇总.json"
    out.write_text(json.dumps(
        [{"config": n, "run_id": r, "summary": s} for n, r, s in rows],
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("汇总文件：%s" % out)


if __name__ == "__main__":
    main()
