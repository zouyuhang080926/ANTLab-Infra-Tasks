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
    "P03": {"type": "code",      "mode": "interactive", "file": None,      "max_tokens": 1536},
    "P04": {"type": "code",      "mode": "interactive", "file": None,      "max_tokens": 2048},
    "D01": {"type": "office",    "mode": "batch",       "file": "办公输入01-项目会议与进度资料.md", "max_tokens": 2048},
    "D02": {"type": "office",    "mode": "batch",       "file": "办公输入01-项目会议与进度资料.md", "max_tokens": 1536},
    "D03": {"type": "office",    "mode": "interactive", "file": "办公输入02-工作室内部管理制度.md", "max_tokens": 1536},
    "D04": {"type": "office",    "mode": "batch",       "file": "办公输入02-工作室内部管理制度.md", "max_tokens": 1536},
    "C01": {"type": "code",      "mode": "batch",       "file": "编程输入03-ticket_stats.py",       "max_tokens": 2048},
    "C02": {"type": "code",      "mode": "batch",       "file": "编程输入03-ticket_stats.py",       "max_tokens": 4096},
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
        "workload_version": "v2",
        "frozen_at": "2026-10-09",
        "revision_note": (
            "v1 首轮基线中 P02、P03、P04、C01、C02 五条任务的输出被输出上限截断"
            "（finish_reason=length），导致输出质量无法检查。v2 提高这五条的输出预算："
            "P02 1024→2048、P03 768→1536、P04 1024→2048、C01 1024→2048、C02 2048→4096；"
            "D01 1536→2048、D03/D04 1024→1536 为留出余量。v1 的基线数据保留在 "
            "results/runs/ 中，不覆盖。"
        ),
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
