#!/usr/bin/env python3
"""
make_flowchart.py —— 生成项目流程图

  图 4：系统架构与数据流（组件之间怎么连）
  图 5：实验闭环（一次实验怎么走，本次项目在每一步得到了什么）

用法：
    python3 src/make_flowchart.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

DEV_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = DEV_DIR / "reports" / "figures"

FONT = "/mnt/c/Windows/Fonts/msyh.ttc"
if Path(FONT).exists():
    fm.fontManager.addfont(FONT)
    plt.rcParams["font.family"] = fm.FontProperties(fname=FONT).get_name()
plt.rcParams["axes.unicode_minus"] = False

C_SRC, C_CFG, C_RUN = "#f3f4f6", "#dbeafe", "#1d4ed8"
C_REC, C_ANA, C_SHOW = "#fef3c7", "#dcfce7", "#fce7f3"
C_SIDE, C_WARN = "#ede9fe", "#fed7aa"
C_LINE = "#374151"


def box(ax, x, y, w, h, text, fc, tc="#111111", fs=10, bold=False, ec="#9ca3af", lw=1.0):
    ax.add_patch(FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.004,rounding_size=0.03",
        linewidth=lw, edgecolor=ec, facecolor=fc, zorder=2))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=tc,
            zorder=3, fontweight="bold" if bold else "normal", linespacing=1.55)


def arrow(ax, x1, y1, x2, y2, label="", fs=8, lx=0.0, ly=0.0, color=C_LINE, ls="-"):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=13,
        linewidth=1.2, color=color, linestyle=ls, zorder=1,
        shrinkA=0, shrinkB=0))
    if label:
        ax.text((x1 + x2) / 2 + lx, (y1 + y2) / 2 + ly, label,
                ha="center", va="center", fontsize=fs, color="#4b5563",
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none"),
                zorder=4)


def line(ax, pts, color=C_LINE, ls="-", lw=1.2):
    for i in range(len(pts) - 1):
        (x1, y1), (x2, y2) = pts[i], pts[i + 1]
        ax.plot([x1, x2], [y1, y2], color=color, linestyle=ls,
                linewidth=lw, zorder=1, solid_capstyle="round")


def fig_architecture():
    fig, ax = plt.subplots(figsize=(10.4, 11.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14.6)
    ax.axis("off")

    # 层标签放在左侧竖排，避免被箭头穿过
    def layer(y, text):
        ax.text(0.12, y, text, ha="left", va="center", fontsize=10.5,
                color="#6b7280", fontweight="bold")

    layer(13.85, "① 素材层")
    box(ax, 5.35, 13.85, 8.4, 0.7,
        "题包（官方素材）：10 条规定任务　+　3 份输入文档（含 SHA256）", C_SRC)

    layer(12.55, "② 配置层")
    box(ax, 5.35, 12.5, 8.4, 1.0,
        "configs/workload.json（v5）：任务定义 · 消息模板 · 生成参数 · 文件校验值\n"
        "scenario.md（场景）　metrics.md（指标口径）　env.md（环境）", C_CFG, fs=9.5)
    arrow(ax, 5.35, 13.5, 5.35, 13.0, "build_workload.py 自动生成 + 逐字校验", lx=2.5)

    layer(11.15, "③ 执行层")
    box(ax, 3.15, 10.75, 4.6, 1.55,
        "runner.py　压测程序\n① dry-run 核查输入\n② 预热（显卡升频）\n"
        "③ 流式发请求\n④ 逐条记录（失败也落盘）",
        C_RUN, tc="white", fs=9.5, bold=True, ec="#1d4ed8")
    box(ax, 8.35, 11.35, 3.0, 0.95, "llama-server :8888\nQwen3-4B · CUDA\n统一 KV 池",
        "#e0e7ff", fs=9)
    arrow(ax, 5.45, 11.05, 6.85, 11.35, "HTTP")

    box(ax, 8.35, 10.25, 3.0, 0.95, "supervisor.py\n健康检测 · 重启\n就绪确认",
        C_SIDE, fs=8.8)
    box(ax, 8.35, 9.15, 3.0, 0.95, "scheduler.py + replay.py\nFIFO / 优先级 / 缓存感知",
        C_SIDE, fs=8.8)
    arrow(ax, 8.35, 9.78, 8.35, 10.02, "")

    layer(8.15, "④ 记录层")
    box(ax, 5.35, 8.05, 8.4, 1.45,
        "results/　（原始数据：只增不改，失败与截断同样保留）\n"
        "runs/ 逐请求记录 + 显卡状态快照　　optimization/ 配置对比\n"
        "quality_check/ 质量核查　　fault_test/ 故障恢复　　advanced/ 调度实验",
        C_REC, fs=9.3)
    arrow(ax, 3.15, 9.97, 3.15, 8.78)

    layer(6.5, "⑤ 分析层")
    box(ax, 1.85, 5.9, 3.0, 0.95, "check_quality.py\n条款引用核对\n代码实际运行",
        C_ANA, fs=8.8)
    box(ax, 5.35, 5.9, 2.6, 0.95, "compare_\noptimization.py\n配置对比汇总",
        C_ANA, fs=8.8)
    box(ax, 8.85, 5.9, 3.0, 0.95, "make_figures.py\nmake_flowchart.py\n报告配图",
        C_ANA, fs=8.8)
    for x in (1.85, 5.35, 8.85):
        arrow(ax, x, 7.32, x, 6.38)

    layer(4.45, "⑥ 展示层")
    box(ax, 5.35, 4.35, 8.4, 1.15,
        "frontend.py :8000　（只用 Python 标准库）\n"
        "服务状态 · 运行列表 · 逐请求记录（含模型原始输出）· 性能统计 · 错误记录 · 基线对比",
        C_SHOW, fs=9.3)
    line(ax, [(1.85, 5.42), (1.85, 4.93), (1.4, 4.93)])
    line(ax, [(8.85, 5.42), (8.85, 4.93), (9.3, 4.93)])
    arrow(ax, 5.35, 5.42, 5.35, 4.93)

    box(ax, 5.35, 2.95, 5.2, 0.72, "reports/report.md　整合报告（基础 + 进阶）",
        "#f9fafb", fs=10, bold=True, ec="#6b7280")
    arrow(ax, 5.35, 3.77, 5.35, 3.32)

    ax.text(5.35, 2.05,
            "数据流：素材 → 配置 → 执行 → 记录 → 分析 → 展示 → 报告\n"
            "任何改动都必须重新冻结配置；原始记录只增不改，失败同样保留",
            ha="center", fontsize=9, color="#6b7280", linespacing=1.8)

    ax.text(5.35, 1.0,
            "约束：单张 12GB 显存笔记本　|　全部源码仅用 Python 标准库　|　"
            "每次运行都留存显卡状态快照",
            ha="center", fontsize=8.5, color="#9ca3af")

    fig.tight_layout()
    fig.savefig(OUT_DIR / "fig4_architecture.png", bbox_inches="tight")
    plt.close(fig)


def fig_loop():
    fig, ax = plt.subplots(figsize=(11.0, 8.6))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 9.2)
    ax.axis("off")

    steps = [
        ("① 提出假设", "换顺序 / 改参数，会带来什么变化？", C_CFG),
        ("② 冻结配置", "负载 v5 固定，服务参数一次只改一项", C_CFG),
        ("③ 预热", "显卡升频需 6~8 秒；丢弃前几条请求", "#e0e7ff"),
        ("④ 采集", "3 轮相同负载；失败与截断同样落盘", C_RUN),
        ("⑤ 核查", "输入对不对？输出能不能用？", C_ANA),
        ("⑥ 归因", "是配置效果，还是设备漂移？", C_WARN),
        ("⑦ 决定", "保留 / 放弃，并写清代价", C_REC),
    ]

    x0, w, h = 3.0, 4.3, 0.86
    ys = [8.35 - i * 1.22 for i in range(len(steps))]

    for (y, (title, desc, color)) in zip(ys, steps):
        box(ax, x0, y, w, h, "%s　%s" % (title, desc), color, fs=9.2,
            tc="white" if color == C_RUN else "#111111")

    for i in range(len(steps) - 1):
        arrow(ax, x0, ys[i] - h / 2, x0, ys[i + 1] + h / 2)

    # 回环箭头：从"⑦ 决定"回到"① 提出假设"
    back_x = 0.55
    line(ax, [(x0 - w / 2, ys[-1]), (back_x, ys[-1]),
              (back_x, ys[0]), (x0 - w / 2, ys[0])])
    ax.add_patch(FancyArrowPatch(
        (back_x + 0.35, ys[0]), (x0 - w / 2, ys[0]),
        arrowstyle="-|>", mutation_scale=13, linewidth=1.2,
        color=C_LINE, zorder=1, shrinkA=0, shrinkB=0))
    ax.text(back_x - 0.05, (ys[0] + ys[-1]) / 2, "闭环", rotation=90,
            ha="center", va="center", fontsize=9, color="#6b7280")

    # 右侧：本次项目走过的四轮
    ax.add_patch(FancyBboxPatch(
        (5.75, 1.05), 5.0, 7.35,
        boxstyle="round,pad=0.02,rounding_size=0.06",
        linewidth=1.4, edgecolor="#1d4ed8", facecolor="#f8fafc", zorder=2))
    ax.text(8.25, 7.95, "本次项目走了四轮", ha="center", fontsize=11.5,
            fontweight="bold", color="#1d4ed8", zorder=3)

    rounds = [
        ("第一轮 · 基线", "单并发 vs 四并发各 3 轮\n"
                      "→ 吞吐 2.06 倍；首字延迟 +10 倍"),
        ("第二轮 · 优化", "Flash Attention 与 KV 量化\n"
                      "→ 推翻预期：FA 是负优化；KV 量化容量翻倍"),
        ("第三轮 · 质量与故障", "输出质量核查 + 运行中杀进程\n"
                          "→ 条款 0 编造；恢复 2.5~3.0 秒"),
        ("第四轮 · 调度", "FIFO / 优先级 / 缓存感知\n"
                      "→ 期限达成率 56% → 100%"),
    ]
    y = 7.05
    for title, desc in rounds:
        ax.text(6.05, y, title, ha="left", fontsize=9.6,
                fontweight="bold", color="#1d4ed8", zorder=3)
        ax.text(6.05, y - 0.42, desc, ha="left", fontsize=8.6,
                color="#374151", linespacing=1.5, zorder=3)
        y -= 1.55

    ax.text(8.25, 0.42,
            "闭环的关键：每一步都要能回答「凭什么说这个改动有用」",
            ha="center", fontsize=9.5, color="#6b7280")

    fig.tight_layout()
    fig.savefig(OUT_DIR / "fig5_experiment_loop.png", bbox_inches="tight")
    plt.close(fig)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig_architecture()
    fig_loop()
    for p in sorted(OUT_DIR.glob("fig[45]*.png")):
        print("已生成：%s" % p)


if __name__ == "__main__":
    main()
