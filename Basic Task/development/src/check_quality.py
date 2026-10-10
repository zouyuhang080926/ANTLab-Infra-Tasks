#!/usr/bin/env python3
"""
check_quality.py —— 输出质量核查

做两类检查：

  一、引用编号核对（办公类 D03/D04）
      制度问答要求"每一步注明相关条款编号"。把答案里出现的编号逐个拿去原文查，
      原文中不存在的就是编造。

  二、代码核查（编程类 P03/P04/C01/C02）
      **不同任务的"合格"标准不同**，这一点很关键：

      | 任务 | 任务要求               | 合格标准                     |
      |------|------------------------|------------------------------|
      | P03  | 完整函数 + 5 个测试    | 代码可以实际运行通过         |
      | C02  | 完整程序 + 补测试      | 程序与测试可以实际运行通过   |
      | P04  | 方案设计 + 核心代码示例 | 代码是示意性的，通过语法检查 |
      | C01  | 指出问题 + 最小复现输入 | 片段是复现输入，逐个检查语法 |

      用统一标准去要求这四类任务，会产生大量假失败。

用法：
    python3 src/check_quality.py [运行编号]
"""

import ast
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DEV_DIR = Path(__file__).resolve().parent.parent
RUNS_DIR = DEV_DIR / "results" / "runs"
CHECK_DIR = DEV_DIR / "results" / "quality_check"
INPUT_DIR = DEV_DIR.parent / "提示词与输入文档" / "输入文档"

BLOCK = re.compile(r"```(?:[a-zA-Z]*)\r?\n(.*?)```", re.S)
CLAUSE = re.compile(r"\b([A-Z]\d{2})\b")
TEST_FUNC = re.compile(r"^\s*def\s+test_", re.M)
IMPORT_FROM = re.compile(r"^\s*from\s+(\w+)\s+import", re.M)

CLAUSE_TASKS = {
    "D03": "办公输入02-工作室内部管理制度.md",
    "D04": "办公输入02-工作室内部管理制度.md",
}

# C01 的任务是"按功能约定逐项指出问题"。原始实现里预埋的缺陷清单，
# 用来检查答案的覆盖情况。**这是关键词近似匹配，不是严格的语义判断**，
# 只能说明"提没提到"，不能说明"分析得对不对"。
C01_ISSUES = {
    "id 去重": ["去重", "重复", "duplicate", "dedup", "唯一"],
    "owner 空值归一": ["unassigned"],
    "status 归一": ["大小写", "lower", "strip", "去除空格", "未知状态"],
    "平均耗时算法": ["分母", "两位小数", "round", "int("],
    "空输入/除零": ["空输入", "空列表", "ZeroDivision", "除零", "除以零"],
    "无效时间": ["时区", "解析失败", "无效时间", "ValueError", "不可解析"],
}


# ---------------------------------------------------------------------------
def latest_run():
    files = sorted(glob.glob(str(RUNS_DIR / "*.jsonl")), key=os.path.getmtime)
    if not files:
        sys.exit("找不到任何运行记录")
    return Path(files[-1]).stem


def check_c01(records):
    """检查代码审查任务的问题覆盖情况。"""
    print("=" * 74)
    print("一之二、代码审查的问题覆盖（关键词近似判断）")
    print("=" * 74)
    results = []
    for r in records:
        if r["task_id"] != "C01" or r["status"] != "ok":
            continue
        answer = r["answer"] or ""
        hit, miss = [], []
        for issue, kws in C01_ISSUES.items():
            (hit if any(k.lower() in answer.lower() for k in kws) else miss).append(issue)
        print("  C01 轮%d：覆盖 %d/%d 项" % (r["round"], len(hit), len(C01_ISSUES)))
        print("        提到：%s" % "、".join(hit))
        if miss:
            print("        未提：%s" % "、".join(miss))
        results.append({"round": r["round"], "hit": hit, "miss": miss})
    print()
    return results


def check_clauses(records):
    print("=" * 74)
    print("一、引用编号核对（制度问答）")
    print("=" * 74)
    results = []

    for task_id, filename in CLAUSE_TASKS.items():
        source_codes = set(CLAUSE.findall((INPUT_DIR / filename).read_text(encoding="utf-8")))
        for r in records:
            if r["task_id"] != task_id or r["status"] != "ok":
                continue
            answer = r["answer"] or ""
            cited = sorted(set(CLAUSE.findall(answer)))
            invalid = [c for c in cited if c not in source_codes]
            print("  %s 轮%d：引用 %2d 个编号 → %s" % (
                task_id, r["round"], len(cited),
                "全部存在于原文" if not invalid else "!! 原文中不存在：" + "、".join(invalid)))
            results.append({"task_id": task_id, "round": r["round"],
                            "cited": cited, "invalid": invalid})
    if not results:
        print("  （无可核查记录）")
    print()
    return results


def run_python(path, timeout=120):
    try:
        proc = subprocess.run([sys.executable, str(path)],
                              capture_output=True, text=True, timeout=timeout)
        return proc.returncode, (proc.stderr or proc.stdout).strip()
    except subprocess.TimeoutExpired:
        return None, "运行超时"


def syntax_ok(code):
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as exc:
        return False, "第 %s 行：%s" % (exc.lineno, exc.msg)


def check_code(run_id, records):
    print("=" * 74)
    print("二、代码核查")
    print("=" * 74)

    out_dir = CHECK_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for r in records:
        task_id, rnd = r["task_id"], r["round"]
        if task_id not in ("P03", "P04", "C01", "C02") or r["status"] != "ok":
            continue
        answer = r["answer"] or ""
        blocks = BLOCK.findall(answer)
        label = "%s_r%d" % (task_id, rnd)

        if not blocks:
            print("  %-8s 没有完整代码块（可能被截断）" % label)
            results.append({"task_id": task_id, "round": rnd, "verdict": "no_code"})
            continue

        # --- P03：期望整套代码能跑 ---
        if task_id == "P03":
            path = out_dir / (label + ".py")
            path.write_text("\n\n".join(blocks), encoding="utf-8")
            rc, msg = run_python(path)
            ok = rc == 0
            print("  %-8s %d 个代码块 → 实际运行：%s" % (label, len(blocks), "通过" if ok else "报错"))
            if not ok:
                print("            %s" % (msg.splitlines() or ["(无输出)"])[-1][:100])
            results.append({"task_id": task_id, "round": rnd,
                            "verdict": "pass" if ok else "error",
                            "blocks": len(blocks), "file": str(path),
                            "detail": msg.splitlines()[-3:] if msg else []})
            continue

        # --- C02：程序与测试分成两个文件，用 pytest 跑 ---
        if task_id == "C02":
            case_dir = out_dir / label
            case_dir.mkdir(exist_ok=True)
            test_block = next((b for b in blocks if TEST_FUNC.search(b)), None)
            prog_block = next((b for b in blocks if b is not test_block), None)
            if not test_block or not prog_block:
                print("  %-8s 没能区分出程序与测试（块数 %d）" % (label, len(blocks)))
                results.append({"task_id": task_id, "round": rnd,
                                "verdict": "unparsed", "blocks": len(blocks)})
                continue
            m = IMPORT_FROM.search(test_block)
            module = m.group(1) if m else "solution"
            (case_dir / (module + ".py")).write_text(prog_block, encoding="utf-8")
            (case_dir / ("test_" + module + ".py")).write_text(test_block, encoding="utf-8")

            try:
                proc = subprocess.run(
                    [sys.executable, "-m", "pytest", "-q", "--no-header",
                     "test_" + module + ".py"],
                    cwd=case_dir, capture_output=True, text=True, timeout=180)
                ok = proc.returncode == 0
                tail = [l for l in (proc.stdout or "").strip().splitlines() if l.strip()]
                print("  %-8s 程序 %d 行 + 测试 %d 行 → pytest：%s" % (
                    label, prog_block.count("\n"), test_block.count("\n"),
                    "全部通过" if ok else "有失败"))
                if tail:
                    print("            %s" % tail[-1][:100])
                results.append({"task_id": task_id, "round": rnd,
                                "verdict": "pass" if ok else "fail",
                                "module": module, "dir": str(case_dir),
                                "summary": tail[-1][:160] if tail else "",
                                "returncode": proc.returncode})
            except Exception as exc:                          # noqa: BLE001
                print("  %-8s 无法运行 pytest：%s" % (label, exc))
                results.append({"task_id": task_id, "round": rnd,
                                "verdict": "cannot_run", "detail": str(exc)})
            continue

        # --- C01：复现片段，是原文件里截出的缩进代码，不要求独立运行 ---
        if task_id == "C01":
            path = out_dir / (label + "_fragments.py")
            path.write_text("\n\n# ----- 下一个片段 -----\n\n".join(blocks), encoding="utf-8")
            print("  %-8s %d 个复现片段（原文件内部的缩进代码，不要求独立运行）"
                  % (label, len(blocks)))
            results.append({"task_id": task_id, "round": rnd,
                            "verdict": "fragments", "blocks": len(blocks),
                            "file": str(path)})
            continue

        # --- P04：方案设计题，代码是示意性的，只检查语法 ---
        good, bad = 0, []
        for i, b in enumerate(blocks, 1):
            ok, msg = syntax_ok(b)
            if ok:
                good += 1
            else:
                bad.append((i, msg))
        path = out_dir / (label + ".py")
        path.write_text("\n\n".join(blocks), encoding="utf-8")
        print("  %-8s %d 个代码块 → 语法正确 %d 个（示意代码，不做运行要求）"
              % (label, len(blocks), good))
        for i, msg in bad:
            print("            块%d：%s" % (i, msg[:90]))
        results.append({"task_id": task_id, "round": rnd,
                        "verdict": "syntax_ok" if not bad else "syntax_error",
                        "blocks": len(blocks), "good": good, "file": str(path)})

    print()
    return results


def main():
    run_id = sys.argv[1] if len(sys.argv) > 1 else latest_run()
    path = RUNS_DIR / (run_id + ".jsonl")
    if not path.exists():
        sys.exit("找不到运行记录：%s" % path)

    records = [json.loads(line) for line in path.open(encoding="utf-8")]
    print("运行编号：%s　共 %d 条记录" % (run_id, len(records)))
    print()

    c01 = check_c01(records)
    clause = check_clauses(records)
    code = check_code(run_id, records)

    out = CHECK_DIR / (run_id + "_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"run_id": run_id, "c01_coverage": c01,
         "clause_refs": clause, "code_checks": code},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("=" * 74)
    print("汇总")
    print("=" * 74)
    print("  引用编号错误：%d 处" % sum(len(c["invalid"]) for c in clause))
    by_task = {}
    for c in code:
        by_task.setdefault(c["task_id"], []).append(c["verdict"])
    for t, vs in by_task.items():
        print("  %-5s %s" % (t, "  ".join(vs)))
    print("  报告文件：%s" % out)


if __name__ == "__main__":
    main()
