# 测试空输入
def test_empty_input():
    assert summarize_tickets([]) == {
        "total": 0,
        "by_status": {name: 0 for name in STATUSES},
        "by_owner": {},
        "average_closed_hours": None
    }

# 测试有效工单缺少 owner、status 或 closed_at
def test_missing_fields():
    record = {
        "id": "T001",
        "owner": "Chen",
        "status": "closed",
        "created_at": "2026-10-12T09:00:00+08:00",
        "closed_at": "2026-10-12T11:30:00+08:00",
    }
    summary = summarize_tickets([record])
    assert summary["total"] == 1
    assert summary["by_status"]["closed"] == 1
    assert summary["by_status"]["open"] == 0
    assert summary["by_status"]["processing"] == 0
    assert summary["by_status"]["other"] == 0
    assert summary["by_owner"]["Chen"]["total"] == 1
    assert summary["average_closed_hours"] is not None

# 测试处理人为空字符串、None 或只含空格
def test_empty_owner():
    record = {
        "id": "T001",
        "owner": "",
        "status": "closed",
        "created_at": "2026-10-12T09:00:00+08:00",
        "closed_at": "2026-10-12T11:30:00+08:00",
    }
    summary = summarize_tickets([record])
    assert summary["by_owner"]["unassigned"]["total"] == 1

# 测试状态含首尾空格、大小写变化或未知值
def test_status_case_and_whitespace():
    record = {
        "id": "T001",
        "owner": "Chen",
        "status": "CLOSED",
        "created_at": "2026-10-12T09:00:00+08:00",
        "closed_at": "2026-10-12T11:30:00+08:00",
    }
    summary = summarize_tickets([record])
    assert summary["by_status"]["closed"] == 1

# 测试相同 id 重复出现，以及 id 缺失或只含空格
def test_duplicate_ids():
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
        {
            "id": "T002",
            "owner": "Chen",
            "status": "closed",
            "created_at": "2026-10-12T09:00:00+08:00",
            "closed_at": "2026-10-12T11:30:00+08:00",
        },
    ]
    summary = summarize_tickets(records)
    assert summary["total"] == 2
    assert summary["by_status"]["closed"] == 2
    assert summary["by_owner"]["Chen"]["total"] == 2

# 测试未关闭工单带有遗留的 closed_at 字段
def test_closed_at_in_open():
    record = {
        "id": "T001",
        "owner": "Chen",
        "status": "open",
        "created_at": "2026-10-12T09:00:00+08:00",
        "closed_at": "2026-10-12T11:30:00+08:00",
    }
    summary = summarize_tickets([record])
    assert summary["by_status"]["open"] == 1
    assert summary["by_status"]["closed"] == 0

# 测试关闭工单缺少时间或时间格式错误
def test_invalid_closed_at():
    record = {
        "id": "T001",
        "owner": "Chen",
        "status": "closed",
        "created_at": "2026-10-12T09:00:00+08:00",
        "closed_at": "invalid_time",
    }
    summary = summarize_tickets([record])
    assert summary["by_status"]["closed"] == 0
    assert summary["by_status"]["other"] == 1

# 测试创建时间和关闭时间使用不同的 UTC 偏移
def test_different_timezone():
    record = {
        "id": "T001",
        "owner": "Chen",
        "status": "closed",
        "created_at": "2026-10-12T09:00:00+08:00",
        "closed_at": "2026-10-12T11:30:00+09:00",
    }
    summary = summarize_tickets([record])
    assert summary["by_status"]["closed"] == 1
    assert summary["average_closed_hours"] is not None

# 测试时间缺少时区，以及关闭时间早于创建时间
def test_invalid_time_format():
    record = {
        "id": "T001",
        "owner": "Chen",
        "status": "closed",
        "created_at": "2026-10-12T09:00:00",
        "closed_at": "2026-10-12T08:30:00",
    }
    summary = summarize_tickets([record])
    assert summary["by_status"]["closed"] == 0
    assert summary["by_status"]["other"] == 1

# 测试输入仅包含没有有效耗时的工单
def test_no_valid_hours():
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
            "owner": "Chen",
            "status": "closed",
            "created_at": "2026-10-12T09:00:00+08:00",
            "closed_at": "2026-10-12T11:30:00+08:00",
        },
    ]
    summary = summarize_tickets(records)
    assert summary["average_closed_hours"] is None
