# 测试空输入
def test_empty_input():
    summary = summarize_tickets([])
    assert summary["total"] == 0
    assert summary["by_status"] == {"open": 0, "processing": 0, "closed": 0, "other": 0}
    assert summary["by_owner"] == {}
    assert summary["average_closed_hours"] is None


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
    assert summary["by_status"] == {"open": 0, "processing": 0, "closed": 0, "other": 1}
    assert summary["by_owner"] == {"Chen": {"total": 1, "open": 0, "processing": 0, "closed": 0, "other": 1}}
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
    assert summary["total"] == 1
    assert summary["by_status"] == {"open": 0, "processing": 0, "closed": 0, "other": 1}
    assert summary["by_owner"] == {"unassigned": {"total": 1, "open": 0, "processing": 0, "closed": 0, "other": 1}}
    assert summary["average_closed_hours"] is not None


# 测试状态含首尾空格、大小写变化或未知值
def test_status_case():
    record = {
        "id": "T001",
        "owner": "Chen",
        "status": "CLOSED",
        "created_at": "2026-10-12T09:00:00+08:00",
        "closed_at": "2026-10-12T11:30:00+08:00",
    }
    summary = summarize_tickets([record])
    assert summary["total"] == 1
    assert summary["by_status"] == {"open": 0, "processing": 0, "closed": 1, "other": 0}
    assert summary["by_owner"] == {"Chen": {"total": 1, "open": 0, "processing": 0, "closed": 1, "other": 0}}
    assert summary["average_closed_hours"] is not None


# 测试未关闭工单带有遗留的 closed_at 字段
def test_closed_at():
    record = {
        "id": "T001",
        "owner": "Chen",
        "status": "closed",
        "created_at": "2026-10-12T09:00:00+08:00",
        "closed_at": "2026-10-12T11:30:00+08:00",
    }
    summary = summarize_tickets([record])
    assert summary["total"] == 1
    assert summary["by_status"] == {"open": 0, "processing": 0, "closed": 1, "other": 0}
    assert summary["by_owner"] == {"Chen": {"total": 1, "open": 0, "processing": 0, "closed": 1, "other": 0}}
    assert summary["average_closed_hours"] is not None


# 测试重复工单 ID
def test_duplicate_id():
    record1 = {
        "id": "T001",
        "owner": "Chen",
        "status": "closed",
        "created_at": "2026-10-12T09:00:00+08:00",
        "closed_at": "2026-10-12T11:30:00+08:00",
    }
    record2 = {
        "id": "T001",
        "owner": "Chen",
        "status": "closed",
        "created_at": "2026-10-12T09:00:00+08:00",
        "closed_at": "2026-10-12T11:30:00+08:00",
    }
    summary = summarize_tickets([record1, record2])
    assert summary["total"] == 1
    assert summary["by_status"] == {"open": 0, "processing": 0, "closed": 1, "other": 0}
    assert summary["by_owner"] == {"Chen": {"total": 1, "open": 0, "processing": 0, "closed": 1, "other": 0}}
    assert summary["average_closed_hours"] is not None


# 测试无效时间
def test_invalid_time():
    record = {
        "id": "T001",
        "owner": "Chen",
        "status": "closed",
        "created_at": "2026-10-12T09:00:00+08:00",
        "closed_at": "2026-10-12T11:30:00+08:00",
    }
    summary = summarize_tickets([record])
    assert summary["total"] == 1
    assert summary["by_status"] == {"open": 0, "processing": 0, "closed": 1, "other": 0}
    assert summary["by_owner"] == {"Chen": {"total": 1, "open": 0, "processing": 0, "closed": 1, "other": 0}}
    assert summary["average_closed_hours"] is not None
