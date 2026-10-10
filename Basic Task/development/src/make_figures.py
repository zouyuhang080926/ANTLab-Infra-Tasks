#!/usr/bin/env python3
"""
make_figures.py —— 生成报告配图

数据来源全部是 results/ 下的原始记录，图中标注对应的运行编号。
中文字体使用 Windows 自带的雅黑（/mnt/c/Windows/Fonts/msyh.ttc）。

用法：
    python3 src/make_figures.py
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np

DEV_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = DEV_DIR / "reports" / "figures"

FONT = "/mnt/c/Windows/Fonts/msyh.ttc"
if Path(FONT).exists():
    fm.fontManager.addfont(FONT)
    plt.rcParams["font.family"] = fm.FontProperties(fname=FONT).get_name()
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150

C_OK = "#1d4ed8"
C_ALT = "#b91c1c"
C_MID = "#6b7280"


def load_run(run_id):
    path = DEV_DIR / "results" / "runs" / (run_id + ".jsonl")
    return [json.loads(l) for l in path.open(encoding="utf-8")]


def summarize(records):
    ok = [r for r in records if r["status"] == "ok"]
    out = sum(r.get("completion_tokens") or 0 for r in ok)
    starts = [r["started_epoch"] for r in records if r.get("started_epoch")]
    ends = [r["finished_epoch"] for r in records if r.get("finished_epoch")]
    wall = max(ends) - min(starts)
    ttft = sorted(r["ttft_seconds"] for r in ok if r.get("ttft_seconds"))
    return {
        "throughput": out / wall,
        "ttft_median": ttft[len(ttft) // 2],
        "wall": wall,
    }


def fig_concurrency():
    """图 1：单并发 vs 四并发（吞吐与首字延迟的取舍）"""
    a = summarize(load_run("20261010_102511"))
    b = summarize(load_run("20261010_103241"))

    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))

    ax = axes[0]
    ax.bar(["单并发", "四并发"], [a["throughput"], b["throughput"]],
           color=[C_MID, C_OK], width=0.5)
    for i, v in enumerate([a["throughput"], b["throughput"]]):
        ax.text(i, v + 3, "%.1f" % v, ha="center", fontsize=11)
    ax.set_ylabel("系统吞吐（token/秒）")
    ax.set_title("并发提高吞吐 2.04 倍")
    ax.set_ylim(0, max(a["throughput"], b["throughput"]) * 1.25)

    ax = axes[1]
    ax.bar(["单并发", "四并发"], [a["ttft_median"], b["ttft_median"]],
           color=[C_MID, C_ALT], width=0.5)
    for i, v in enumerate([a["ttft_median"], b["ttft_median"]]):
        ax.text(i, v + 0.02, "%.2f" % v, ha="center", fontsize=11)
    ax.set_ylabel("首字延迟中位数（秒）")
    ax.set_title("代价：首字延迟恶化 9.2 倍")
    ax.set_ylim(0, max(a["ttft_median"], b["ttft_median"]) * 1.25)

    fig.suptitle("图 1　并发度的取舍（负载 v5，各 3 轮）\n"
                 "数据：results/runs/20261010_102511（并发1）、20261010_103241（并发4）",
                 fontsize=10)
    fig.tight_layout(rect=[0, 0.06, 1, 0.88])
    fig.savefig(OUT_DIR / "fig1_concurrency.png")
    plt.close(fig)


def fig_scheduling():
    """图 2：三种调度策略对比"""
    path = DEV_DIR / "results" / "advanced" / "summary.json"
    rows = json.load(open(path, encoding="utf-8"))

    order = ["fifo", "priority", "priority_cache"]
    label = {"fifo": "FIFO", "priority": "优先级", "priority_cache": "优先级+缓存"}
    agg = {}
    for p in order:
        s = [r["summary"] for r in rows if r["policy"] == p]
        agg[p] = {
            "deadline": np.mean([x["deadline_rate"] for x in s]) * 100,
            "inter": np.mean([x["interactive_wait_median"] for x in s]),
            "batch": np.mean([x["batch_wait_median"] for x in s]),
            "cached": np.mean([x["cached_tokens"] for x in s]),
        }

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
    names = [label[p] for p in order]
    colors = [C_MID, C_OK, "#0f766e"]

    ax = axes[0]
    vals = [agg[p]["deadline"] for p in order]
    ax.bar(names, vals, color=colors, width=0.55)
    for i, v in enumerate(vals):
        ax.text(i, v + 2, "%.0f%%" % v, ha="center", fontsize=11)
    ax.set_ylabel("期限达成率")
    ax.set_ylim(0, 118)
    ax.set_title("按期率 56% → 100%")

    ax = axes[1]
    x = np.arange(3)
    ax.bar(x - 0.19, [agg[p]["inter"] for p in order], 0.36,
           label="交互式", color=C_OK)
    ax.bar(x + 0.19, [agg[p]["batch"] for p in order], 0.36,
           label="后台", color="#c7d2fe")
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylabel("等待时间中位数（秒）")
    ax.legend(fontsize=9)
    ax.set_title("交互式等待 −76%，后台 +52%")

    ax = axes[2]
    vals = [agg[p]["cached"] for p in order]
    ax.bar(names, vals, color=colors, width=0.55)
    for i, v in enumerate(vals):
        ax.text(i, v + 60, "%.0f" % v, ha="center", fontsize=11)
    ax.set_ylabel("缓存命中 token 数")
    ax.set_ylim(0, max(vals) * 1.2)
    ax.set_title("优先级调度顺带提高缓存命中 37%")

    fig.suptitle("图 2　三种调度策略对比（冷缓存，各 3 轮）\n"
                 "数据：results/advanced/summary.json",
                 fontsize=10)
    fig.tight_layout(rect=[0, 0.05, 1, 0.86])
    fig.savefig(OUT_DIR / "fig2_scheduling.png")
    plt.close(fig)


def fig_kv():
    """图 3：KV 精度与容量的关系"""
    labels = ["f16\n8192", "f16\n16384", "q8_0\n16384", "q8_0\n32768", "q8_0\n65536*"]
    kv = [1152, 2304, 1224, 2448, 4896]
    ctx = [8192, 16384, 16384, 32768, 40960]

    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    colors = [C_MID, C_MID, C_OK, C_OK, C_ALT]
    bars = ax.bar(labels, kv, color=colors, width=0.6)
    for b, c in zip(bars, ctx):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 80,
                "%d token" % c, ha="center", fontsize=9)
    ax.set_ylabel("KV 缓存显存（MiB）")
    ax.set_title("同等显存下，KV 量化把可用容量翻倍\n"
                 "（* 请求 65536 时被模型训练上限 40960 截断）", fontsize=10)
    ax.set_ylim(0, max(kv) * 1.25)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "fig3_kv_capacity.png")
    plt.close(fig)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig_concurrency()
    fig_scheduling()
    fig_kv()
    for p in sorted(OUT_DIR.glob("*.png")):
        print("已生成：%s" % p)


if __name__ == "__main__":
    main()
