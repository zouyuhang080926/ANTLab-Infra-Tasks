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
            "closed_at": None
        }
    ]
    summary = summarize_tickets(records)
    assert summary["total"] == 1
    assert summary["by_status"]["closed"] == 1
    assert summary["by_status"]["other"] == 0
    assert summary["by_status"]["open"] == 0
    assert summary["by_status"]["processing"] == 0
    assert summary["by_owner"]["Chen"] == {"total": 1, "open": 0, "processing": 0, "closed": 1, "other": 0}
    assert summary["average_closed_hours"] is None

def test_unassigned_owner():
    records = [
        {
            "id": "T001",
            "owner": "",
            "status": "closed",
            "created_at": "2026-10-12T09:00:00+08:00",
            "closed_at": "2026-10-12T11:30:00+08:00"
        }
    ]
    summary = summarize_tickets(records)
    assert summary["by_owner"]["unassigned"] == {"total": 1, "open": 0, "processing": 0, "closed": 1, "other": 0}

def test_unknown_status():
    records = [
        {
            "id": "T001",
            "owner": "Chen",
            "status": "closed",
            "created_at": "2026-10-12T09:00:00+08:00",
            "closed_at": "2026-10-12T11:30:00+08:00"
        }
    ]
    summary = summarize_tickets(records)
    assert summary["by_status"]["closed"] == 1
    assert summary["by_status"]["other"] == 0
    assert summary["by_status"]["open"] == 0
    assert summary["by_status"]["processing"] == 0

def test_duplicate_id():
    records = [
        {
            "id": "T001",
            "owner": "Chen",
            "status": "closed",
            "created_at": "2026-10-12T09:00:00+08:00",
            "closed_at": "2026-10-12T11:30:00+08:00"
        },
        {
            "id": "T001",
            "owner": "Chen",
            "status": "closed",
            "created_at": "2026-10-12T09:00:00+08:00",
            "closed_at": "2026-10-12T11:30:00+08:00"
        }
    ]
    summary = summarize_tickets(records)
    assert summary["total"] == 1
    assert summary["by_status"]["closed"] == 1
    assert summary["by_status"]["other"] == 0
    assert summary["by_status"]["open"] == 0
    assert summary["by_status"]["processing"] == 0
    assert summary["by_owner"]["Chen"] == {"total": 1, "open": 0, "processing": 0, "closed": 1, "other": 0}

def test_open_status():
    records = [
        {
            "id": "T001",
            "owner": "Chen",
            "status": "open",
            "created_at": "2026-10-12T09:00:00+08:00",
            "closed_at": None
        }
    ]
    summary = summarize_tickets(records)
    assert summary["by_status"]["open"] == 1
    assert summary["by_status"]["other"] == 0
    assert summary["by_status"]["closed"] == 0
    assert summary["by_status"]["processing"] == 0
    assert summary["by_owner"]["Chen"] == {"total": 1, "open": 1, "processing": 0, "closed": 0, "other": 0}

def test_closed_at_missing():
    records = [
        {
            "id": "T001",
            "owner": "Chen",
            "status": "closed",
            "created_at": "2026-10-12T09:00:00+08:00",
            "closed_at": None
        }
    ]
    summary = summarize_tickets(records)
    assert summary["by_status"]["closed"] == 1
    assert summary["by_status"]["other"] == 0
    assert summary["by_status"]["open"] == 0
    assert summary["by_status"]["processing"] == 0
    assert summary["by_owner"]["Chen"] == {"total": 1, "open": 0, "processing": 0, "closed": 1, "other": 0}
    assert summary["average_closed_hours"] is None

def test_invalid_time():
    records = [
        {
            "id": "T001",
            "owner": "Chen",
            "status": "closed",
            "created_at": "2026-10-12T09:00:00+08:00",
            "closed_at": "2026-10-12T08:30:00+08:00"
        }
    ]
    summary = summarize_tickets(records)
    assert summary["by_status"]["closed"] == 1
    assert summary["by_status"]["other"] == 0
    assert summary["by_status"]["open"] == 0
    assert summary["by_status"]["processing"] == 0
    assert summary["by_owner"]["Chen"] == {"total": 1, "open": 0, "processing": 0, "closed": 1, "other": 0}
    assert summary["average_closed_hours"] is None
