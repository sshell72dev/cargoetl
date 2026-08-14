from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.leaderboard import (
    build_leaderboard,
    competition_ranks,
    default_period,
    load_margin,
    period_bounds,
)


CHICAGO = ZoneInfo("America/Chicago")


def dispatcher(did="D-01", name="Ada", hired="2025-01-01", tz="America/Chicago", status="active"):
    return {
        "id": did,
        "name": name,
        "hiredAt": hired,
        "status": status,
        "timezone": tz,
    }


def load(
    lid,
    status="delivered",
    booked_by="D-01",
    closed_by="D-01",
    booked_at="2026-07-10T12:00:00+00:00",
    delivered_at="2026-07-12T18:00:00+00:00",
    customer=2500,
    driver=2000,
    miles=500,
):
    return {
        "id": lid,
        "status": status,
        "bookedBy": booked_by,
        "closedBy": closed_by,
        "bookedAt": booked_at,
        "pickupAt": booked_at,
        "deliveredAt": delivered_at if status == "delivered" else None,
        "customerRate": customer,
        "driverPay": driver,
        "miles": miles,
        "origin": "A",
        "destination": "B",
    }


def test_margin_is_customer_minus_driver_including_losses():
    assert load_margin({"customerRate": 2450, "driverPay": 1900}) == 550
    assert load_margin({"customerRate": 1400, "driverPay": 1680}) == -280


def test_handoff_credits_closer_not_booker():
    people = [
        dispatcher("D-01", "Marcus"),
        dispatcher("D-02", "Priya"),
    ]
    loads = [
        load(
            "L-HANDOFF",
            booked_by="D-02",
            closed_by="D-01",
            customer=3200,
            driver=2500,
        )
    ]
    board = build_leaderboard(people, loads, "2026-07")
    by_id = {row["dispatcher"]["id"]: row for row in board["rows"]}
    assert by_id["D-01"]["margin"] == 700
    assert by_id["D-01"]["loadsClosed"] == 1
    assert by_id["D-01"]["handoffsIn"] == 1
    assert by_id["D-02"]["loadsClosed"] == 0
    assert by_id["D-02"]["margin"] == 0
    assert by_id["D-02"]["handoffsOut"] == 1
    assert "L-HANDOFF" in board["countedLoadIds"]


def test_timezone_boundary_uses_company_clock_not_dispatcher_clock():
    """
    2026-08-01T04:30:00Z is 23:30 CDT on July 31 in Chicago,
    but 00:30 EDT on August 1 in New York.

    Ranking money uses America/Chicago. An Eastern dispatcher does not
    pull the load into August just because their local clock rolled over.
    """
    people = [dispatcher("D-02", "Priya", tz="America/New_York")]
    loads = [
        load(
            "L-TZ-BOMB",
            booked_by="D-02",
            closed_by="D-02",
            booked_at="2026-07-29T16:10:00+00:00",
            delivered_at="2026-08-01T04:30:00+00:00",
            customer=2450,
            driver=1900,
        )
    ]
    july = build_leaderboard(people, loads, "2026-07")
    august = build_leaderboard(people, loads, "2026-08")
    assert july["rows"][0]["margin"] == 550
    assert july["rows"][0]["loadsClosed"] == 1
    assert august["rows"][0]["loadsClosed"] == 0
    assert august["rows"][0]["margin"] == 0

    start, end = period_bounds("2026-07")
    assert start.tzinfo == CHICAGO
    assert end.isoformat().startswith("2026-08-01T00:00:00")


def test_cancelled_and_missing_closer_are_excluded_and_explained():
    people = [dispatcher("D-01", "Marcus"), dispatcher("D-11", "Kelly")]
    loads = [
        load("L-OK", customer=2000, driver=1500),
        load(
            "L-CANCEL",
            status="cancelled",
            booked_by="D-01",
            closed_by=None,
            delivered_at=None,
            customer=2800,
            driver=2100,
        ),
        load(
            "L-NO-CLOSER",
            booked_by="D-11",
            closed_by=None,
            customer=1900,
            driver=1500,
        ),
    ]
    board = build_leaderboard(people, loads, "2026-07")
    reasons = {item["reason"] for item in board["excluded"]["samples"]}
    assert reasons == {"cancelled", "missing_closer"}
    assert board["company"]["loads"] == 1
    assert board["company"]["margin"] == 500
    assert "L-OK" in board["countedLoadIds"]
    assert "L-NO-CLOSER" not in board["countedLoadIds"]


def test_competition_rank_shares_place_and_skips():
    assert competition_ranks([100, 90, 90, 70]) == [1, 2, 2, 4]


def test_new_hire_is_ranked_on_total_margin_but_flagged_partial():
    people = [
        dispatcher("D-01", "Marcus", hired="2025-01-01"),
        dispatcher("D-24", "Jade", hired="2026-07-16", tz="America/Los_Angeles"),
    ]
    loads = [
        load("L-OLD", booked_by="D-01", closed_by="D-01", customer=5000, driver=4000),
        load(
            "L-NEW",
            booked_by="D-24",
            closed_by="D-24",
            booked_at="2026-07-17T18:00:00+00:00",
            delivered_at="2026-07-20T21:00:00+00:00",
            customer=3600,
            driver=2700,
        ),
    ]
    board = build_leaderboard(people, loads, "2026-07")
    by_id = {row["dispatcher"]["id"]: row for row in board["rows"]}
    assert by_id["D-01"]["rank"] == 1
    assert by_id["D-24"]["rank"] == 2
    assert by_id["D-24"]["partialPeriod"] is True
    assert by_id["D-24"]["newHire"] is True
    assert by_id["D-24"]["daysActive"] == 16  # Jul 16 .. Aug 1
    assert by_id["D-01"]["partialPeriod"] is False
    # Pace is higher for the new hire — visible, but not the official sort
    assert by_id["D-24"]["marginPerActiveDay"] > by_id["D-01"]["marginPerActiveDay"]


def test_default_period_is_last_full_month():
    now = datetime(2026, 8, 14, 18, 0, tzinfo=timezone.utc)
    assert default_period(now) == "2026-07"


def test_generated_july_has_forced_tie_and_timezone_bomb():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    dispatchers = json.loads((root / "data" / "dispatchers.json").read_text(encoding="utf-8"))
    loads = json.loads((root / "data" / "loads.json").read_text(encoding="utf-8"))
    board = build_leaderboard(dispatchers, loads, "2026-07")
    by_id = {row["dispatcher"]["id"]: row for row in board["rows"]}
    assert by_id["D-09"]["margin"] == by_id["D-10"]["margin"]
    assert by_id["D-09"]["rank"] == by_id["D-10"]["rank"]
    assert by_id["D-09"]["tied"] is True
    assert "L-TZ-BOMB" in board["countedLoadIds"]
    assert "L-HANDOFF-01" in board["countedLoadIds"]
    assert "L-CROSS-MONTH" not in board["countedLoadIds"]
    assert "L-NO-CLOSER" not in board["countedLoadIds"]
    assert by_id["D-24"]["partialPeriod"] is True
    reasons = {item["reason"] for item in board["excluded"]["summary"]}
    assert "cancelled" in reasons
    assert "missing_closer" in reasons
