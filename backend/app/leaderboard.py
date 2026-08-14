from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

COMPANY_TZ = ZoneInfo("America/Chicago")


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"naive timestamp is not allowed: {value}")
    return dt


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    month += delta
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return year, month


def period_bounds(period: str, tz: ZoneInfo = COMPANY_TZ) -> tuple[datetime, datetime]:
    year, month = (int(part) for part in period.split("-"))
    start = datetime(year, month, 1, tzinfo=tz)
    end_year, end_month = _shift_month(year, month, 1)
    end = datetime(end_year, end_month, 1, tzinfo=tz)
    return start, end


def previous_period(period: str) -> str:
    year, month = (int(part) for part in period.split("-"))
    year, month = _shift_month(year, month, -1)
    return f"{year:04d}-{month:02d}"


def default_period(now: datetime) -> str:
    """Last fully closed calendar month on the company clock."""
    local = now.astimezone(COMPANY_TZ)
    year, month = _shift_month(local.year, local.month, -1)
    return f"{year:04d}-{month:02d}"


def in_period(ts: datetime | None, start: datetime, end: datetime) -> bool:
    if ts is None:
        return False
    return start <= ts.astimezone(start.tzinfo) < end


def money(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def load_margin(load: dict) -> float:
    return money(load["customerRate"] - load["driverPay"])


def days_active_in_period(dispatcher: dict, start: datetime, end: datetime) -> int:
    hired = datetime.strptime(dispatcher["hiredAt"], "%Y-%m-%d").replace(tzinfo=start.tzinfo)
    left = end
    if dispatcher.get("terminatedAt"):
        terminated = datetime.strptime(dispatcher["terminatedAt"], "%Y-%m-%d").replace(
            tzinfo=start.tzinfo
        )
        left = min(left, terminated)
    active_start = max(start, hired)
    if active_start >= left:
        return 0
    return (left - active_start).days


def competition_ranks(sorted_margins: list[float]) -> list[int]:
    """1, 2, 2, 4 — shared place, next rank skipped."""
    ranks: list[int] = []
    for index, margin in enumerate(sorted_margins):
        if index > 0 and margin == sorted_margins[index - 1]:
            ranks.append(ranks[-1])
        else:
            ranks.append(index + 1)
    return ranks


def classify_exclusion(load: dict, start: datetime, end: datetime) -> dict | None:
    """
    Loads that touched the period but did not enter the ranking.
    Touch = booked, delivered, or cancelled inside the window.
    """
    booked = parse_dt(load.get("bookedAt"))
    delivered = parse_dt(load.get("deliveredAt"))
    status = load["status"]

    booked_here = in_period(booked, start, end)
    delivered_here = in_period(delivered, start, end)

    if status == "cancelled":
        if booked_here:
            return {
                "loadId": load["id"],
                "reason": "cancelled",
                "detail": "Cancelled loads never realize margin.",
                "bookedBy": load.get("bookedBy"),
                "closedBy": load.get("closedBy"),
                "margin": load_margin(load),
            }
        return None

    if status == "delivered":
        if delivered_here and not load.get("closedBy"):
            return {
                "loadId": load["id"],
                "reason": "missing_closer",
                "detail": "Delivered, but closedBy is empty — cannot attribute a bonus.",
                "bookedBy": load.get("bookedBy"),
                "closedBy": None,
                "margin": load_margin(load),
            }
        if booked_here and delivered and not delivered_here:
            return {
                "loadId": load["id"],
                "reason": "deferred_to_delivery_month",
                "detail": "Booked in this period, delivered later. Counts in the delivery month.",
                "bookedBy": load.get("bookedBy"),
                "closedBy": load.get("closedBy"),
                "margin": load_margin(load),
                "deliveredAt": load.get("deliveredAt"),
            }
        return None

    if booked_here:
        return {
            "loadId": load["id"],
            "reason": "not_delivered",
            "detail": f"Status is '{status}'. Only delivered loads enter the ranking.",
            "bookedBy": load.get("bookedBy"),
            "closedBy": load.get("closedBy"),
            "margin": load_margin(load),
        }
    return None


def empty_bucket(dispatcher: dict) -> dict:
    return {
        "dispatcher": dispatcher,
        "margin": 0.0,
        "loadsClosed": 0,
        "miles": 0,
        "lossLoads": 0,
        "handoffsIn": 0,
        "handoffsOut": 0,
        "bookedLoads": 0,
        "bookedMargin": 0.0,
        "loadIds": [],
    }


def accumulate(dispatchers: list[dict], loads: list[dict], start: datetime, end: datetime) -> dict:
    by_id = {d["id"]: empty_bucket(d) for d in dispatchers}
    counted: list[dict] = []
    excluded: list[dict] = []

    for load in loads:
        delivered = parse_dt(load.get("deliveredAt"))
        booked = parse_dt(load.get("bookedAt"))
        status = load["status"]
        margin = load_margin(load)
        booker_id = load.get("bookedBy")
        closer_id = load.get("closedBy")

        if status == "delivered" and in_period(delivered, start, end) and closer_id:
            bucket = by_id.get(closer_id)
            if bucket:
                bucket["margin"] = money(bucket["margin"] + margin)
                bucket["loadsClosed"] += 1
                bucket["miles"] += int(load.get("miles") or 0)
                bucket["loadIds"].append(load["id"])
                if margin < 0:
                    bucket["lossLoads"] += 1
                if booker_id and booker_id != closer_id:
                    bucket["handoffsIn"] += 1
                    if booker_id in by_id:
                        by_id[booker_id]["handoffsOut"] += 1
                counted.append(
                    {
                        "loadId": load["id"],
                        "closedBy": closer_id,
                        "bookedBy": booker_id,
                        "margin": margin,
                        "handoff": bool(booker_id and booker_id != closer_id),
                    }
                )

        if (
            status == "delivered"
            and in_period(booked, start, end)
            and booker_id
            and booker_id in by_id
        ):
            by_id[booker_id]["bookedLoads"] += 1
            by_id[booker_id]["bookedMargin"] = money(by_id[booker_id]["bookedMargin"] + margin)

        exclusion = classify_exclusion(load, start, end)
        if exclusion:
            excluded.append(exclusion)

    for bucket in by_id.values():
        bucket["margin"] = money(bucket["margin"])
        bucket["bookedMargin"] = money(bucket["bookedMargin"])

    return {"buckets": by_id, "counted": counted, "excluded": excluded}


def rank_buckets(buckets: dict[str, dict], start: datetime, end: datetime) -> list[dict]:
    period_days = (end - start).days
    eligible = []
    for bucket in buckets.values():
        dispatcher = bucket["dispatcher"]
        active_days = days_active_in_period(dispatcher, start, end)
        if active_days <= 0 and bucket["loadsClosed"] == 0:
            continue
        eligible.append((bucket, active_days))

    eligible.sort(
        key=lambda item: (
            -item[0]["margin"],
            -item[0]["loadsClosed"],
            item[0]["dispatcher"]["name"],
        )
    )
    ranks = competition_ranks([item[0]["margin"] for item in eligible])

    rows = []
    for rank, (bucket, active_days) in zip(ranks, eligible):
        loads_closed = bucket["loadsClosed"]
        miles = bucket["miles"]
        margin = bucket["margin"]
        hired = datetime.strptime(bucket["dispatcher"]["hiredAt"], "%Y-%m-%d").date()
        rows.append(
            {
                "rank": rank,
                "dispatcher": {
                    "id": bucket["dispatcher"]["id"],
                    "name": bucket["dispatcher"]["name"],
                    "status": bucket["dispatcher"]["status"],
                    "hiredAt": bucket["dispatcher"]["hiredAt"],
                    "terminatedAt": bucket["dispatcher"].get("terminatedAt"),
                    "timezone": bucket["dispatcher"]["timezone"],
                },
                "margin": margin,
                "loadsClosed": loads_closed,
                "avgMargin": money(margin / loads_closed) if loads_closed else 0.0,
                "rpm": money(margin / miles) if miles else 0.0,
                "miles": miles,
                "marginPerActiveDay": money(margin / active_days) if active_days else 0.0,
                "daysActive": active_days,
                "periodDays": period_days,
                "partialPeriod": active_days < period_days,
                "newHire": start.date() <= hired < end.date(),
                "handoffsIn": bucket["handoffsIn"],
                "handoffsOut": bucket["handoffsOut"],
                "lossLoads": bucket["lossLoads"],
                "bookedLoads": bucket["bookedLoads"],
                "bookedMargin": bucket["bookedMargin"],
                "tied": False,
            }
        )

    rank_counts = Counter(row["rank"] for row in rows)
    for row in rows:
        row["tied"] = rank_counts[row["rank"]] > 1
    return rows


def attach_rank_delta(current: list[dict], previous: list[dict]) -> None:
    prev_rank = {row["dispatcher"]["id"]: row["rank"] for row in previous}
    for row in current:
        did = row["dispatcher"]["id"]
        if did not in prev_rank:
            row["previousRank"] = None
            row["rankDelta"] = None
            row["rankDeltaLabel"] = "new"
            continue
        previous_rank = prev_rank[did]
        delta = previous_rank - row["rank"]  # positive = moved up
        row["previousRank"] = previous_rank
        row["rankDelta"] = delta
        if delta > 0:
            row["rankDeltaLabel"] = f"+{delta}"
        elif delta < 0:
            row["rankDeltaLabel"] = str(delta)
        else:
            row["rankDeltaLabel"] = "="


def summarize_excluded(excluded: list[dict]) -> list[dict]:
    grouped: dict[str, dict] = defaultdict(lambda: {"count": 0, "margin": 0.0})
    for item in excluded:
        grouped[item["reason"]]["count"] += 1
        grouped[item["reason"]]["margin"] = money(
            grouped[item["reason"]]["margin"] + item.get("margin", 0)
        )
    labels = {
        "cancelled": "Cancelled — no realized margin",
        "not_delivered": "Still open — not delivered in this period",
        "missing_closer": "Delivered with no closer — unattributed",
        "deferred_to_delivery_month": "Booked here, delivered later",
    }
    return [
        {
            "reason": reason,
            "label": labels.get(reason, reason),
            "count": payload["count"],
            "margin": payload["margin"],
        }
        for reason, payload in grouped.items()
    ]


def build_leaderboard(
    dispatchers: list[dict],
    loads: list[dict],
    period: str,
) -> dict:
    start, end = period_bounds(period)
    current = accumulate(dispatchers, loads, start, end)
    prev_id = previous_period(period)
    prev_start, prev_end = period_bounds(prev_id)
    previous = accumulate(dispatchers, loads, prev_start, prev_end)

    rows = rank_buckets(current["buckets"], start, end)
    prev_rows = rank_buckets(previous["buckets"], prev_start, prev_end)
    attach_rank_delta(rows, prev_rows)

    counted_margin = money(sum(item["margin"] for item in current["counted"]))
    notes = []
    tied_ranks = sorted({row["rank"] for row in rows if row["tied"]})
    if tied_ranks:
        notes.append(
            "Shared rank "
            + ", ".join(f"#{r}" for r in tied_ranks)
            + " — same closed margin to the cent. Competition ranking (1, 2, 2, 4)."
        )
    partial = [row for row in rows if row["partialPeriod"] and row["loadsClosed"] > 0]
    if partial:
        notes.append(
            f"{len(partial)} dispatcher(s) were not on the roster the full month. "
            "Official rank is still total margin; use $/day to compare pace."
        )
    missing = [item for item in current["excluded"] if item["reason"] == "missing_closer"]
    if missing:
        notes.append(
            f"{len(missing)} delivered load(s) have no closer and were left out of bonuses."
        )

    return {
        "period": {
            "id": period,
            "label": start.strftime("%B %Y"),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "timezone": "America/Chicago",
            "previousPeriod": prev_id,
        },
        "rules": {
            "attribution": "closedBy",
            "periodField": "deliveredAt",
            "timezone": "America/Chicago",
            "includeNegativeMargin": True,
            "ranking": "competition",
        },
        "company": {
            "margin": counted_margin,
            "loads": len(current["counted"]),
            "miles": sum(row["miles"] for row in rows),
            "rpm": money(
                counted_margin / sum(row["miles"] for row in rows)
                if sum(row["miles"] for row in rows)
                else 0
            ),
            "excludedCount": len(current["excluded"]),
            "dispatchersRanked": len(rows),
        },
        "rows": rows,
        "excluded": {
            "summary": summarize_excluded(current["excluded"]),
            "samples": current["excluded"][:40],
            "total": len(current["excluded"]),
        },
        "notes": notes,
        "countedLoadIds": [item["loadId"] for item in current["counted"]],
    }


def available_periods(loads: list[dict], now: datetime) -> list[str]:
    months = set()
    for load in loads:
        delivered = parse_dt(load.get("deliveredAt"))
        booked = parse_dt(load.get("bookedAt"))
        for ts in (delivered, booked):
            if ts is None:
                continue
            local = ts.astimezone(COMPANY_TZ)
            months.add(f"{local.year:04d}-{local.month:02d}")
    months.add(default_period(now))
    return sorted(months)


def build_dashboard(leaderboard: dict, previous_leaderboard: dict) -> dict:
    rows = leaderboard["rows"]
    prev_rows = {row["dispatcher"]["id"]: row for row in previous_leaderboard["rows"]}
    top3 = rows[:3]
    movers = sorted(
        [row for row in rows if isinstance(row.get("rankDelta"), int)],
        key=lambda row: (-row["rankDelta"], row["rank"]),
    )
    company = leaderboard["company"]
    prev_company = previous_leaderboard["company"]
    return {
        "period": leaderboard["period"],
        "company": {
            **company,
            "previousMargin": prev_company["margin"],
            "marginDelta": money(company["margin"] - prev_company["margin"]),
            "previousLoads": prev_company["loads"],
            "loadsDelta": company["loads"] - prev_company["loads"],
        },
        "top3": top3,
        "biggestClimber": movers[0] if movers and movers[0]["rankDelta"] > 0 else None,
        "biggestDrop": movers[-1] if movers and movers[-1]["rankDelta"] < 0 else None,
        "newHires": [row for row in rows if row["newHire"]],
        "partialPeriod": [row for row in rows if row["partialPeriod"]],
        "lossLeaders": sorted(
            [row for row in rows if row["lossLoads"] > 0],
            key=lambda row: -row["lossLoads"],
        )[:5],
        "notes": leaderboard["notes"],
        "excluded": leaderboard["excluded"]["summary"],
        "rules": leaderboard["rules"],
    }


def dispatcher_detail(
    dispatcher_id: str,
    dispatchers: list[dict],
    loads: list[dict],
    leaderboard: dict,
) -> dict | None:
    dispatcher = next((d for d in dispatchers if d["id"] == dispatcher_id), None)
    if dispatcher is None:
        return None
    row = next((r for r in leaderboard["rows"] if r["dispatcher"]["id"] == dispatcher_id), None)
    start, end = period_bounds(leaderboard["period"]["id"])
    own_loads = []
    for load in loads:
        booked = parse_dt(load.get("bookedAt"))
        delivered = parse_dt(load.get("deliveredAt"))
        involved = load.get("bookedBy") == dispatcher_id or load.get("closedBy") == dispatcher_id
        if not involved:
            continue
        if not (in_period(booked, start, end) or in_period(delivered, start, end)):
            continue
        counted = (
            load["status"] == "delivered"
            and in_period(delivered, start, end)
            and load.get("closedBy") == dispatcher_id
        )
        reason = None
        if not counted:
            if load["status"] == "cancelled":
                reason = "cancelled"
            elif load["status"] != "delivered":
                reason = "not_delivered"
            elif load.get("closedBy") != dispatcher_id:
                reason = "credited_to_closer"
            elif not in_period(delivered, start, end):
                reason = "outside_period"
        own_loads.append(
            {
                "id": load["id"],
                "status": load["status"],
                "origin": load["origin"],
                "destination": load["destination"],
                "miles": load["miles"],
                "customerRate": load["customerRate"],
                "driverPay": load["driverPay"],
                "margin": load_margin(load),
                "bookedBy": load.get("bookedBy"),
                "closedBy": load.get("closedBy"),
                "bookedAt": load.get("bookedAt"),
                "deliveredAt": load.get("deliveredAt"),
                "counted": counted,
                "excludeReason": reason,
                "handoff": load.get("bookedBy") != load.get("closedBy")
                and bool(load.get("closedBy")),
            }
        )
    own_loads.sort(key=lambda item: item.get("deliveredAt") or item.get("bookedAt") or "")
    return {
        "dispatcher": dispatcher,
        "row": row,
        "period": leaderboard["period"],
        "loads": own_loads,
        "countedLoads": [item for item in own_loads if item["counted"]],
        "excludedLoads": [item for item in own_loads if not item["counted"]],
    }
