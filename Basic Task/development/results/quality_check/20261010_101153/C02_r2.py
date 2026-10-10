from datetime import datetime
import json


STATUSES = ("open", "processing", "closed", "other")


def parse_time(value):
    """将时间字符串转换为 datetime。"""
    return datetime.fromisoformat(value)


def ticket_hours(record):
    """读取一条工单的处理耗时，单位为小时。"""
    start = parse_time(record["created_at"])
    end = parse_time(record["closed_at"])
    return (end - start).total_seconds() / 3600


def summarize_tickets(records):
    """按状态、处理人汇总，并计算平均处理耗时。"""
    by_status = {name: 0 for name in STATUSES}
    by_owner = {}
    hours = []

    for record in records:
        # 去重处理
        if record.get("id") and record["id"].strip():
            # 检查是否已经处理过该id
            if record["id"].strip() in [r["id"].strip() for r in records if r.get("id") and r["id"].strip()]:
                continue

        owner = record.get("owner", "")
        status = record.get("status", "")

        # 处理人归类
        if not owner or owner.strip() == "":
            owner = "unassigned"
        else:
            owner = owner.strip()

        # 状态归类
        if status.strip().lower() in STATUSES:
            status = status.strip().lower()
        else:
            status = "other"

        # 处理人归类
        if owner not in by_owner:
            by_owner[owner] = {
                "total": 0,
                "open": 0,
                "processing": 0,
                "closed": 0,
                "other": 0,
            }

        # 状态统计
        by_status[status] += 1
        by_owner[owner]["total"] += 1
        by_owner[owner][status] += 1

        # 处理耗时统计
        if record.get("closed_at"):
            try:
                hours.append(ticket_hours(record))
            except:
                hours.append(0)
        else:
            hours.append(0)

    # 计算平均耗时
    if len(hours) > 0:
        average = sum(hours) / len(hours)
    else:
        average = None

    return {
        "total": len(records),
        "by_status": by_status,
        "by_owner": by_owner,
        "average_closed_hours": average,
    }


def render_summary(summary):
    """将统计结果转换为可打印的文本。"""
    lines = ["工单统计", f"有效工单总数：{summary['total']}"]
    lines.append("状态分布：")
    for status in STATUSES:
        lines.append(f"  {status}: {summary['by_status'][status]}")
    lines.append("处理人分布：")
    for owner, counts in sorted(summary["by_owner"].items()):
        lines.append(f"  {owner}: {counts['total']}")
    average = summary["average_closed_hours"]
    lines.append(f"平均已关闭工单耗时：{average} 小时")
    return "\n".join(lines)


SAMPLE_RECORDS = [
    {
        "id": "T001",
        "owner": "Chen",
        "status": "closed",
        "created_at": "2026-10-12T09:00:00+08:00",
        "closed_at": "2026-10-12T11:30:00+08:00",
    },
    {
        "id": "T002",
        "owner": "Song",
        "status": "processing",
        "created_at": "2026-10-12T10:00:00+08:00",
        "closed_at": None,
    },
    {
        "id": "T003",
        "owner": "Chen",
        "status": "open",
        "created_at": "2026-10-12T13:00:00+08:00",
        "closed_at": None,
    },
    {
        "id": "T004",
        "owner": "Zhou",
        "status": "closed",
        "created_at": "2026-10-12T14:00:00+08:00",
        "closed_at": "2026-10-12T18:15:00+08:00",
    },
    {
        "id": "T001",
        "owner": "Chen",
        "status": "closed",
        "created_at": "2026-10-12T09:00:00+08:00",
        "closed_at": "2026-10-12T11:30:00+08:00",
    },
]


# 以下情境供测试设计时参考，可自行构造更多组合。
EDGE_SCENARIOS = (
    "输入为空列表",
    "有效工单缺少 owner、status 或 closed_at",
    "处理人为空字符串、None 或只含空格",
    "状态含首尾空格、大小写变化或未知值",
    "相同 id 重复出现，以及 id 缺失或只含空格",
    "未关闭工单带有遗留的 closed_at 字段",
    "关闭工单缺少时间或时间格式错误",
    "创建时间和关闭时间使用不同的 UTC 偏移",
    "时间缺少时区，以及关闭时间早于创建时间",
    "输入仅包含没有有效耗时的工单",
)


def main():
    summary = summarize_tickets(SAMPLE_RECORDS)
    print(render_summary(summary))
    print("\n结构化结果：")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


import pytest
from ticket_stats import summarize_tickets, parse_time, ticket_hours, render_summary

def test_empty_input():
    assert summarize_tickets([]) == {
        "total": 0,
        "by_status": {"open": 0, "processing": 0, "closed": 0, "other": 0},
        "by_owner": {},
        "average_closed_hours": None
    }

def test_missing_fields():
    records = [
        {
            "id": "T001",
            "owner": "Chen",
            "status": "closed",
            "created_at": "2026-10-12T09:00:00+08:00",
            "closed_at": "2026-10-12T11:30:00+08:00",
        },
        {
            "id": "T002",
            "owner": "Song",
            "status": "processing",
            "created_at": "2026-10-12T10:00:00+08:00",
            "closed_at": None,
        },
        {
            "id": "T003",
            "owner": "Chen",
            "status": "open",
            "created_at": "2026-10-12T13:00:00+08:00",
            "closed_at": None,
        },
        {
            "id": "T004",
            "owner": "Zhou",
            "status": "closed",
            "created_at": "2026-10-12T14:00:00+08:00",
            "closed_at": "2026-10-12T18:15:00+08:00",
        },
        {
            "id": "T001",
            "owner": "Chen",
            "status": "closed",
            "created_at": "2026-10-12T09:00:00+08:00",
            "closed_at": "2026-10-12T11:30:00+08:00",
        },
    ]
    summary = summarize_tickets(records)
    assert summary["total"] == 4
    assert summary["by_status"] == {"open": 1, "processing": 1, "closed": 2, "other": 0}
    assert summary["by_owner"] == {
        "Chen": {"total": 2, "open": 1, "processing": 0, "closed": 1, "other": 0},
        "Song": {"total": 1, "open": 0, "processing": 1, "closed": 0, "other": 0},
        "Zhou": {"total": 1, "open": 0, "processing": 0, "closed": 1, "other": 0},
        "unassigned": {"total": 0, "open": 0, "processing": 0, "closed": 0, "other": 0}
    }
    assert summary["average_closed_hours"] == 2.0

def test_owner_processing():
    records = [
        {
            "id": "T001",
            "owner": "Chen",
            "status": "closed",
            "created_at": "2026-10-12T09:00:00+08:00",
            "closed_at": "2026-10-12T11:30:00+08:00",
        },
        {
            "id": "T002",
            "owner": "Song",
            "status": "processing",
            "created_at": "2026-10-12T10:00:00+08:00",
            "closed_at": None,
        },
        {
            "id": "T003",
            "owner": "Chen",
            "status": "open",
            "created_at": "2026-10-12T13:00:00+08:00",
            "closed_at": None,
        },
        {
            "id": "T004",
            "owner": "Zhou",
            "status": "closed",
            "created_at": "2026-10-12T14:00:00+08:00",
            "closed_at": "2026-10-12T18:15:00+08:00",
        },
        {
            "id": "T001",
            "owner": "Chen",
            "status": "closed",
            "created_at": "2026-10-12T09:00:00+08:00",
            "closed_at": "2026-10-12T11:30:00+08:00",
        },
    ]
    summary = summarize_tickets(records)
    assert summary["by_owner"] == {
        "Chen": {"total": 2, "open": 1, "processing": 0, "closed": 1, "other": 0},
        "Song": {"total": 1, "open": 0, "processing": 1, "closed": 0, "other": 0},
        "Zhou": {"total": 1, "open": 0, "processing": 0, "closed": 1, "other": 0},
        "unassigned": {"total": 0, "open": 0, "processing": 0, "closed": 0, "other": 0}
    }

def test_status_processing():
    records = [
        {
            "id": "T001",
            "owner": "Chen",
            "status": "closed",
            "created_at": "2026-10-12T09:00:00+08:00",
            "closed_at": "2026-10-12T11:30:00+08:00",
        },
        {
            "id": "T002",
            "owner": "Song",
            "status": "processing",
            "created_at": "2026-10-12T10:00:00+08:00",
            "closed_at": None,
        },
        {
            "id": "T003",
            "owner": "Chen",
            "status": "open",
            "created_at": "2026-10-12T13:00:00+08:00",
            "closed_at": None,
        },
        {
            "id": "T004",
            "owner": "Zhou",
            "status": "closed",
            "created_at": "2026-10-12T14:00:00+08:00",
            "closed_at": "2026-10-12T18:15:00+08:00",
        },
        {
            "id": "T001",
            "owner": "Chen",
            "status": "closed",
            "created_at": "2026-10-12T09:00:00+08:00",
            "closed_at": "2026-10-12T11:30:00+08:00",
        },
    ]
    summary = summarize_tickets(records)
    assert summary["by_status"] == {"open": 1, "processing": 1, "closed": 2, "other": 0}

def test_invalid_time():
    records = [
        {
            "id": "T001",
            "owner": "Chen",
            "status": "closed",
            "created_at": "2026-10-12T09:00:00+08:00",
            "closed_at": "2026-10-12T11:30:00+08:00",
        },
        {
            "id": "T002",
            "owner": "Song",
            "status": "processing",
            "created_at": "2026-10-12T10:00:00+08:00",
            "closed_at": None,
        },
        {
            "id": "T003",
            "owner": "Chen",
            "status": "open",
            "created_at": "2026-10-12T13:00:00+08:00",
            "closed_at": None,
        },
        {
            "id": "T004",
            "owner": "Zhou",
            "status": "closed",
            "created_at": "2026-10-12T14:00:00+08:00",
            "closed_at": "2026-10-12T18:15:00+08:00",
        },
        {
            "id": "T001",
            "owner": "Chen",
            "status": "closed",
            "created_at": "2026-10-12T09:00:00+08:00",
            "closed_at": "2026-10-12T11:30:00+08:00",
        },
    ]
    summary = summarize_tickets(records)
    assert summary["average_closed_hours"] == 2.0

def test_duplicate_id():
    records = [
        {
            "id": "T001",
            "owner": "Chen",
            "status": "closed",
            "created_at": "2026-10-12T09:00:00+08:00",
            "closed_at": "2026-10-12T11:30:00+08:00",
        },
        {
            "id": "T001",
            "owner": "Chen",
            "status": "closed",
            "created_at": "2026-10-12T09:00:00+08:00",
            "closed_at": "2026-10-12T11:30:00+08:00",
        },
    ]
    summary = summarize_tickets(records)
    assert summary["total"] == 1
    assert summary["by_status"] == {"open": 0, "processing": 0, "closed": 1, "other": 0}
    assert summary["by_owner"] == {"Chen": {"total": 1, "open": 0, "processing": 0, "closed": 1, "other": 0}, "unassigned": {"total": 0, "open": 0, "processing": 0, "closed": 0, "other": 0}}
    assert summary["average_closed_hours"] == 2.0
