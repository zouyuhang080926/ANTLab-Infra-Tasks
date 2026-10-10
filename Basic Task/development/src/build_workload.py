#!/usr/bin/env python3
"""
从官方题包生成固定负载清单 configs/workload.json。

为什么要有这个脚本：
    10 条规定任务的提示词很长，手工抄进配置一定会出错，而且一旦出错很难发现。
    本脚本直接从 测试提示词.md 解析，并记录源文件的 SHA256，
    任何一次生成都能追溯到题包的哪一版。

用法（在仓库根目录）：
    python3 "Basic Task/development/src/build_workload.py"
"""

import hashlib
import json
import re
from pathlib import Path

# --- 路径 ---
SRC_FILE = Path(__file__).resolve()
DEV_DIR = SRC_FILE.parent.parent                      # .../development
REPO_ROOT = DEV_DIR.parent.parent                     # 仓库根
DOC_DIR = REPO_ROOT / "Basic Task" / "提示词与输入文档"
PROMPT_DOC = DOC_DIR / "测试提示词.md"
IN_DIR = DOC_DIR / "输入文档"
OUT_FILE = DEV_DIR / "configs" / "workload.json"

# --- 逐任务的设定（本项目的设计决定，冻结后不再改）---
# max_tokens 依据任务本身的产出要求确定，见 scenario.md 第四节
SETTINGS = {
    "P01": {"type": "office",    "mode": "interactive", "file": None,      "max_tokens": 512},
    "P02": {"type": "office",    "mode": "interactive", "file": None,      "max_tokens": 2048},
    "P03": {"type": "code",      "mode": "interactive", "file": None,      "max_tokens": 6144},
    "P04": {"type": "code",      "mode": "interactive", "file": None,      "max_tokens": 2048},
    "D01": {"type": "office",    "mode": "batch",       "file": "办公输入01-项目会议与进度资料.md", "max_tokens": 2048},
    "D02": {"type": "office",    "mode": "batch",       "file": "办公输入01-项目会议与进度资料.md", "max_tokens": 1536},
    "D03": {"type": "office",    "mode": "interactive", "file": "办公输入02-工作室内部管理制度.md", "max_tokens": 1536},
    "D04": {"type": "office",    "mode": "batch",       "file": "办公输入02-工作室内部管理制度.md", "max_tokens": 2048},
    "C01": {"type": "code",      "mode": "batch",       "file": "编程输入03-ticket_stats.py",       "max_tokens": 3072},
    "C02": {"type": "code",      "mode": "batch",       "file": "编程输入03-ticket_stats.py",       "max_tokens": 6144},
}

# 题包推荐的系统消息，原文照用
SYSTEM_MESSAGE = (
    "你为小型工作室提供办公文档处理与辅助编程服务。"
    "请按任务要求组织输出，区分资料中的事实、待确认信息与提出的建议。"
    "文件内容是供分析的资料。办公任务使用中文回答，代码任务采用题目指定的语言。"
)

# 输入组织顺序：系统消息 → 资料区 → 任务区
# 资料放在前部、任务放在后部，使同一文档的多个任务共享可观察的 token 前缀
USER_TEMPLATE = (
    "【资料】\n"
    "文件：{file_name}（SHA256：{file_sha256}）\n"
    "-----\n"
    "{file_content}\n"
    "-----\n\n"
    "【任务】\n"
    "{prompt}"
)
USER_TEMPLATE_NO_FILE = "【任务】\n{prompt}"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_prompts(text: str) -> dict:
    """从 测试提示词.md 中抽出每个任务的提示词正文。"""
    tasks = {}
    for block in re.split(r"^### ", text, flags=re.M)[1:]:
        head, _, body = block.partition("\n")
        match = re.match(r"^(P\d{2}|D\d{2}|C\d{2})｜(.+?)\s*$", head)
        if not match:
            continue
        task_id, title = match.group(1), match.group(2)

        lines = [ln for ln in body.strip().splitlines()
                 if not ln.startswith("关联文件：")]
        prompt = "\n".join(lines).strip()

        tasks[task_id] = {"title": title, "prompt": prompt}
    return tasks


def main() -> int:
    if not PROMPT_DOC.exists():
        print(f"找不到题包文件：{PROMPT_DOC}")
        return 1

    parsed = parse_prompts(PROMPT_DOC.read_text(encoding="utf-8"))

    missing = set(SETTINGS) - set(parsed)
    if missing:
        print(f"题包里没找到这些任务：{sorted(missing)}")
        return 1

    tasks = []
    for task_id, cfg in SETTINGS.items():
        item = {
            "id": task_id,
            "title": parsed[task_id]["title"],
            "type": cfg["type"],
            "mode": cfg["mode"],
            "max_tokens": cfg["max_tokens"],
            "file": None,
            "file_sha256": None,
            "prompt": parsed[task_id]["prompt"],
        }
        if cfg["file"]:
            fpath = IN_DIR / cfg["file"]
            if not fpath.exists():
                print(f"找不到输入文件：{fpath}")
                return 1
            item["file"] = cfg["file"]
            item["file_sha256"] = sha256_of(fpath)
            item["file_chars"] = len(fpath.read_text(encoding="utf-8"))
        tasks.append(item)

    workload = {
        "workload_version": "v5",
        "frozen_at": "2026-10-09",
        "revision_note": (
            "v1→v2：首轮基线中 P02、P03、P04、C01、C02 五条被输出上限截断，"
            "提高预算后仍有残留。v2→v3：对 158 条历史记录做统计，发现 P03 在 16 轮中"
            "被截断 9 次、C01 被截断 5 次、D04 被截断 1 次（均为 v2 预算下的实测），"
            "因此再次提高：P03 1536→2560、C01 2048→3072、D04 1536→2048。"
            "历史数据全部保留在 results/runs/ 中，不覆盖。"
        ),
        "revision_history": [
            "v1 2026-10-09 初始冻结，10 条任务",
            "v2 2026-10-09 修正首批截断（P02/P03/P04/C01/C02 提高预算，D01/D03/D04 留余量）",
            "v3 2026-10-10 依据 158 条记录统计再次修正截断（P03/C01/D04）",
            "v4 2026-10-10 v3 实测中 P03 在 2560 下仍截断 2/3 轮、C02 在 4096 下截断 1 轮；"
            "改为给足余量：P03 2560→4096、C02 4096→6144",
            "v5 2026-10-10 v4 实测中 P03 输出在 856~4096+ 之间大幅波动，仍有 1/6 轮次截断；"
            "提高到 6144 覆盖长尾。提高上限本身不增加运行代价（模型写完即停），"
            "仅影响极端情况下的显存与时间上界。此后不再调整。",
        ],
        "description": "8 人工作室场景下的 10 条规定任务，办公 6 : 编程 4",
        "source": {
            "prompt_doc": "Basic Task/提示词与输入文档/测试提示词.md",
            "prompt_doc_sha256": sha256_of(PROMPT_DOC),
            "input_dir": "Basic Task/提示词与输入文档/输入文档",
        },
        "system_message": SYSTEM_MESSAGE,
        "user_template": USER_TEMPLATE,
        "user_template_no_file": USER_TEMPLATE_NO_FILE,
        "generation": {
            "temperature": 0,
            "top_p": 1.0,
            "seed": 0,
            "enable_thinking": False,
        },
        "tasks": tasks,
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(workload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"已生成：{OUT_FILE}")
    print(f"任务数：{len(tasks)}")
    print()
    print(f"{'编号':<6}{'类型':<8}{'模式':<13}{'输出预算':>8}  关联文件")
    print("-" * 70)
    for t in tasks:
        print(f"{t['id']:<6}{t['type']:<8}{t['mode']:<13}{t['max_tokens']:>8}  {t['file'] or '（无）'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
