"""Dashboard aggregation (services/dashboard.py).

build_dashboard_rows is a pure function, fed plain tuples and objects: no
database.
"""

from datetime import datetime
from types import SimpleNamespace

from app.models.answer import AnswerStatus
from app.services.dashboard import build_dashboard_rows


def _session(id_, codes, created=datetime(2026, 9, 1)):
    codes_json = "[" + ",".join(f'{{"code": "{c}", "name": "{c}"}}' for c in codes) + "]"
    return SimpleNamespace(
        id=id_,
        session_code=f"S-{id_}",
        name=f"Session {id_}",
        description=None,
        company=SimpleNamespace(name="Fund", management_company_name="Manager"),
        creator=SimpleNamespace(username="analyst"),
        created_by=1,
        assigned_to=None,
        created_at=created,
        dd_types_json=codes_json,
    )


ALPHA = SimpleNamespace(id=38, code="ALPHA", name="Alpha review", is_active=True)
BETA = SimpleNamespace(id=39, code="BETA", name="Beta review", is_active=True)


def test_counts_progress_and_totals():
    sessions = [_session(1, ["ALPHA", "BETA"])]
    executions = [(1, 38, "ALPHA", "Alpha review", True, "generated", datetime(2026, 9, 2))]
    answer_counts = [
        # enum members, as SQLAlchemy returns them, and plain strings
        (1, 38, AnswerStatus.COMPLETED, 60, datetime(2026, 9, 2, 10), None),
        (1, 38, "needs_review", 2, datetime(2026, 9, 2, 11), datetime(2026, 9, 3)),
        (1, 38, AnswerStatus.APPROVED, 8, datetime(2026, 9, 2, 9), datetime(2026, 9, 4)),
        (1, 38, AnswerStatus.FAILED, 2, datetime(2026, 9, 2, 8), None),
    ]
    answered = [(1, 38, 70)]
    summaries = [(1, 38, 1, datetime(2026, 9, 5), datetime(2026, 9, 5))]
    batches = [(1, 38, "collected", datetime(2026, 9, 5))]

    result = build_dashboard_rows(
        sessions,
        executions,
        answer_counts,
        answered,
        summaries,
        batches,
        {38: 72, 39: 133},
        {"ALPHA": ALPHA, "BETA": BETA},
    )

    row = result["sessions"][0]
    alpha = next(d for d in row["dd_types"] if d["code"] == "ALPHA")
    beta = next(d for d in row["dd_types"] if d["code"] == "BETA")

    assert alpha["status"] == "completed"  # generated -> completed
    assert alpha["to_review"] == 62  # completed + needs_review
    assert alpha["approved"] == 8 and alpha["failed"] == 2
    assert alpha["answered"] == 70 and alpha["total_questions"] == 72
    assert alpha["percentage"] == 97
    assert alpha["has_synthesis"] is True
    assert alpha["last_answer_at"] == datetime(2026, 9, 2, 11).isoformat()

    # Selected at creation, never started: listed as not started.
    assert beta["status"] == "not_started" and beta["total_questions"] == 133
    assert beta["percentage"] == 0

    assert row["last_activity_at"] == datetime(2026, 9, 5).isoformat()
    assert row["batch_pending"] is False
    assert result["totals"] == {"sessions": 1, "to_review": 62, "running": 0, "syntheses_ready": 1}


def test_running_pending_batch_and_ordering():
    sessions = [_session(1, ["ALPHA"]), _session(2, ["ALPHA"])]
    executions = [
        (1, 38, "ALPHA", "Alpha review", True, "in_progress", datetime(2026, 9, 1)),
        (2, 38, "ALPHA", "Alpha review", True, "paused", datetime(2026, 9, 10)),
    ]
    batches = [(1, 38, "in_progress", datetime(2026, 9, 2))]

    result = build_dashboard_rows(
        sessions,
        executions,
        [],
        [],
        [],
        batches,
        {38: 72},
        {"ALPHA": ALPHA},
    )

    # Most recent activity first.
    assert [r["id"] for r in result["sessions"]] == [2, 1]
    assert result["sessions"][1]["batch_pending"] is True
    assert result["totals"]["running"] == 1


def test_unknown_or_unreadable_dd_types_are_skipped():
    session = _session(1, [])
    session.dd_types_json = "not json"
    # Answers of a DD type with no execution and no selection: nothing to show.
    result = build_dashboard_rows(
        [session],
        [],
        [(1, 99, "completed", 3, None, None)],
        [],
        [],
        [],
        {},
        {},
    )
    assert result["sessions"][0]["dd_types"] == []
    assert result["totals"]["to_review"] == 0
