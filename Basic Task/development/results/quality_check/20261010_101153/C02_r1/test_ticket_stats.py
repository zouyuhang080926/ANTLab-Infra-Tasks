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
