"""
Reproducible synthetic dataset for the dispatcher leaderboard.

Seed 42. Writes data/dispatchers.json, loads.json, events.json.

Edge cases planted on purpose (see README):
- Handoffs: bookedBy != closedBy
- Month-boundary: booked late July, delivered early August
- Timezone bomb: UTC timestamp on Aug 1 that is still July 31 in America/Chicago
- Cancelled loads, negative-margin loads, missing closer
- Mid-period new hire, terminated dispatcher with residual loads
- Forced identical July margin for two dispatchers
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

SEED = 42
COMPANY_TZ = "America/Chicago"
OUT_DIR = Path(__file__).resolve().parent.parent / "data"

CITIES = [
    ("Chicago, IL", "Dallas, TX", 780),
    ("Atlanta, GA", "Miami, FL", 660),
    ("Los Angeles, CA", "Phoenix, AZ", 370),
    ("Newark, NJ", "Charlotte, NC", 540),
    ("Houston, TX", "Memphis, TN", 570),
    ("Denver, CO", "Kansas City, MO", 610),
    ("Seattle, WA", "Portland, OR", 175),
    ("Indianapolis, IN", "Columbus, OH", 175),
    ("Philadelphia, PA", "Boston, MA", 310),
    ("Nashville, TN", "Jacksonville, FL", 540),
    ("Detroit, MI", "Chicago, IL", 280),
    ("Dallas, TX", "Atlanta, GA", 780),
    ("Phoenix, AZ", "El Paso, TX", 430),
    ("Minneapolis, MN", "St. Louis, MO", 560),
    ("Salt Lake City, UT", "Denver, CO", 520),
    ("Baltimore, MD", "Pittsburgh, PA", 250),
    ("San Antonio, TX", "New Orleans, LA", 540),
    ("Cleveland, OH", "Louisville, KY", 350),
    ("Raleigh, NC", "Savannah, GA", 310),
    ("Oklahoma City, OK", "Little Rock, AR", 340),
]

DISPATCHER_DEFS = [
    # id, name, hired, status, terminated, timezone, skill (volume multiplier)
    ("D-01", "Marcus Hale", "2024-11-04", "active", None, "America/Chicago", 1.25),
    ("D-02", "Priya Shah", "2025-01-13", "active", None, "America/New_York", 1.20),
    ("D-03", "Elena Vasquez", "2025-02-03", "active", None, "America/Los_Angeles", 1.15),
    ("D-04", "Jonah Briggs", "2025-03-17", "active", None, "America/Denver", 1.10),
    ("D-05", "Aisha Bennett", "2025-04-01", "active", None, "America/Chicago", 1.18),
    ("D-06", "Chris Nguyen", "2025-04-22", "active", None, "America/New_York", 1.05),
    ("D-07", "Sofia Alvarez", "2025-05-12", "active", None, "America/Phoenix", 1.12),
    ("D-08", "Derek Walsh", "2025-06-02", "active", None, "America/Chicago", 0.95),
    ("D-09", "Nina Petrov", "2025-06-23", "active", None, "America/Los_Angeles", 1.00),
    ("D-10", "Omar Haddad", "2025-07-14", "active", None, "America/New_York", 1.08),
    ("D-11", "Kelly O'Brien", "2025-08-04", "active", None, "America/Chicago", 0.92),
    ("D-12", "Luis Romero", "2025-08-25", "active", None, "America/Denver", 0.98),
    ("D-13", "Hannah Cho", "2025-09-15", "active", None, "America/Los_Angeles", 1.06),
    ("D-14", "Tyler Grant", "2025-10-06", "active", None, "America/Chicago", 0.88),
    ("D-15", "Amira Hassan", "2025-10-27", "active", None, "America/New_York", 1.02),
    ("D-16", "Brett Coleman", "2025-11-17", "active", None, "America/Chicago", 0.90),
    ("D-17", "Mei Lin", "2025-12-08", "active", None, "America/Los_Angeles", 0.97),
    ("D-18", "Andre Brooks", "2026-01-12", "active", None, "America/New_York", 0.85),
    ("D-19", "Cara Mitchell", "2026-02-02", "active", None, "America/Chicago", 0.93),
    ("D-20", "Jamal Wright", "2026-03-09", "active", None, "America/Denver", 0.87),
    ("D-21", "Riley Fox", "2026-04-13", "active", None, "America/Chicago", 0.80),
    ("D-22", "Samir Patel", "2026-05-18", "active", None, "America/New_York", 0.78),
    # Mid-June hire — partial first month
    ("D-23", "Quinn Murphy", "2026-06-16", "active", None, "America/Chicago", 0.70),
    # Mid-July hire — the fairness case
    ("D-24", "Jade Ortega", "2026-07-16", "active", None, "America/Los_Angeles", 0.75),
    # Terminated mid-June, leftover June loads
    ("D-25", "Victor Lang", "2025-09-01", "terminated", "2026-06-20", "America/Chicago", 0.60),
    # Hired Aug 1 — should not appear in July ranking with loads, only as empty/new
    ("D-26", "Nora Kim", "2026-08-03", "active", None, "America/New_York", 0.65),
]


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def round_money(x: float) -> float:
    return round(x + 1e-9, 2)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def event(load_id: str, etype: str, at: datetime, dispatcher_id: str) -> dict:
    return {
        "id": f"E-{load_id}-{etype}",
        "loadId": load_id,
        "type": etype,
        "at": iso(at),
        "dispatcherId": dispatcher_id,
    }


def make_load(
    load_id: str,
    status: str,
    booked_by: str,
    closed_by: str | None,
    booked_at: datetime,
    pickup_at: datetime | None,
    delivered_at: datetime | None,
    customer_rate: float,
    driver_pay: float,
    miles: int,
    origin: str,
    destination: str,
    tags: list[str],
) -> dict:
    return {
        "id": load_id,
        "status": status,
        "bookedBy": booked_by,
        "closedBy": closed_by,
        "bookedAt": iso(booked_at),
        "pickupAt": iso(pickup_at) if pickup_at else None,
        "deliveredAt": iso(delivered_at) if delivered_at else None,
        "customerRate": round_money(customer_rate),
        "driverPay": round_money(driver_pay),
        "miles": miles,
        "origin": origin,
        "destination": destination,
        "tags": tags,
    }


def lane(rng: random.Random) -> tuple[str, str, int]:
    origin, dest, miles = rng.choice(CITIES)
    jitter = rng.randint(-25, 40)
    return origin, dest, max(80, miles + jitter)


def rate_for(miles: int, rng: random.Random, quality: float = 1.0) -> tuple[float, float]:
    rpm = rng.uniform(2.35, 3.55) * quality
    customer = miles * rpm
    take = rng.uniform(0.18, 0.32)
    driver = customer * (1 - take)
    return round_money(customer), round_money(driver)


def active_dispatchers_on(day: datetime, dispatchers: list[dict]) -> list[dict]:
    out = []
    for d in dispatchers:
        hired = parse_date(d["hiredAt"])
        if day < hired:
            continue
        if d["status"] == "terminated" and d.get("terminatedAt"):
            if day >= parse_date(d["terminatedAt"]):
                continue
        out.append(d)
    return out


def build_events_for_load(load: dict, rng: random.Random) -> list[dict]:
    booked_at = datetime.fromisoformat(load["bookedAt"].replace("+00:00", "+00:00"))
    events = [event(load["id"], "booked", booked_at, load["bookedBy"])]
    closer = load["closedBy"] or load["bookedBy"]

    if load["status"] == "cancelled":
        cancel_at = booked_at + timedelta(hours=rng.randint(2, 36))
        events.append(event(load["id"], "cancelled", cancel_at, closer))
        return events

    assigned_at = booked_at + timedelta(minutes=rng.randint(20, 180))
    events.append(event(load["id"], "assigned", assigned_at, closer))

    if load["status"] in ("booked", "assigned"):
        return events

    pickup_at = datetime.fromisoformat(load["pickupAt"])
    events.append(event(load["id"], "picked_up", pickup_at, closer))

    if load["status"] == "picked_up":
        return events

    if load["status"] == "delivered" and load["deliveredAt"]:
        delivered_at = datetime.fromisoformat(load["deliveredAt"])
        events.append(event(load["id"], "delivered", delivered_at, closer))
    return events


def plant_edge_cases(loads: list[dict], events: list[dict], rng: random.Random) -> None:
    """Named loads the README and tests can point at."""

    # 1. Timezone bomb: 04:30 UTC Aug 1 = 23:30 CDT July 31. Counts as July
    #    on the company clock, August for an Eastern dispatcher.
    origin, dest, miles = "Chicago, IL", "Dallas, TX", 780
    booked = datetime(2026, 7, 29, 16, 10, tzinfo=timezone.utc)
    pickup = datetime(2026, 7, 30, 14, 0, tzinfo=timezone.utc)
    delivered = datetime(2026, 8, 1, 4, 30, tzinfo=timezone.utc)
    loads.append(
        make_load(
            "L-TZ-BOMB",
            "delivered",
            "D-02",  # Eastern
            "D-02",
            booked,
            pickup,
            delivered,
            2450.00,
            1900.00,
            miles,
            origin,
            dest,
            ["timezone_boundary", "counts_as_july_chicago"],
        )
    )

    # 2. Classic handoff: Priya booked, Marcus closed
    loads.append(
        make_load(
            "L-HANDOFF-01",
            "delivered",
            "D-02",
            "D-01",
            datetime(2026, 7, 8, 15, 20, tzinfo=timezone.utc),
            datetime(2026, 7, 9, 13, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 11, 22, 40, tzinfo=timezone.utc),
            3200.00,
            2500.00,
            820,
            "Atlanta, GA",
            "Dallas, TX",
            ["handoff"],
        )
    )

    # 3. Booked last hours of July, delivered August — August money
    loads.append(
        make_load(
            "L-CROSS-MONTH",
            "delivered",
            "D-05",
            "D-05",
            datetime(2026, 7, 31, 21, 40, tzinfo=timezone.utc),
            datetime(2026, 8, 1, 15, 0, tzinfo=timezone.utc),
            datetime(2026, 8, 3, 18, 10, tzinfo=timezone.utc),
            2100.00,
            1650.00,
            610,
            "Houston, TX",
            "Memphis, TN",
            ["booked_july_delivered_august"],
        )
    )

    # 4. Negative margin — still real P&L
    loads.append(
        make_load(
            "L-NEG-01",
            "delivered",
            "D-14",
            "D-14",
            datetime(2026, 7, 12, 11, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 13, 9, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 14, 20, 15, tzinfo=timezone.utc),
            1400.00,
            1680.00,
            540,
            "Indianapolis, IN",
            "Columbus, OH",
            ["negative_margin"],
        )
    )

    # 5. Cancelled after booking
    loads.append(
        make_load(
            "L-CANCEL-01",
            "cancelled",
            "D-08",
            None,
            datetime(2026, 7, 19, 14, 5, tzinfo=timezone.utc),
            None,
            None,
            2800.00,
            2100.00,
            780,
            "Chicago, IL",
            "Dallas, TX",
            ["cancelled"],
        )
    )

    # 6. Delivered with missing closer — must not silently vanish
    loads.append(
        make_load(
            "L-NO-CLOSER",
            "delivered",
            "D-11",
            None,
            datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 23, 19, 30, tzinfo=timezone.utc),
            1900.00,
            1500.00,
            430,
            "Phoenix, AZ",
            "El Paso, TX",
            ["missing_closer"],
        )
    )

    # 7. Jade Ortega (new hire July 16) — a solid load so she isn't a ghost
    loads.append(
        make_load(
            "L-NEWHIRE-01",
            "delivered",
            "D-24",
            "D-24",
            datetime(2026, 7, 17, 18, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 18, 14, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 20, 21, 0, tzinfo=timezone.utc),
            3600.00,
            2700.00,
            900,
            "Los Angeles, CA",
            "Dallas, TX",
            ["new_hire"],
        )
    )

    # 8. Terminated dispatcher residual June delivery
    loads.append(
        make_load(
            "L-TERMINATED-01",
            "delivered",
            "D-25",
            "D-25",
            datetime(2026, 6, 17, 12, 0, tzinfo=timezone.utc),
            datetime(2026, 6, 18, 9, 0, tzinfo=timezone.utc),
            datetime(2026, 6, 19, 16, 45, tzinfo=timezone.utc),
            2200.00,
            1750.00,
            560,
            "Denver, CO",
            "Kansas City, MO",
            ["terminated_dispatcher"],
        )
    )

    # 9. Zero-margin load
    loads.append(
        make_load(
            "L-ZERO-MARGIN",
            "delivered",
            "D-16",
            "D-16",
            datetime(2026, 7, 6, 13, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 7, 11, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 8, 17, 20, tzinfo=timezone.utc),
            1800.00,
            1800.00,
            400,
            "Cleveland, OH",
            "Louisville, KY",
            ["zero_margin"],
        )
    )

    for load in loads:
        if load["id"].startswith("L-") and any(
            t in load.get("tags", [])
            for t in (
                "timezone_boundary",
                "handoff",
                "booked_july_delivered_august",
                "negative_margin",
                "cancelled",
                "missing_closer",
                "new_hire",
                "terminated_dispatcher",
                "zero_margin",
            )
        ):
            events.extend(build_events_for_load(load, rng))


def force_july_tie(loads: list[dict]) -> tuple[str, str]:
    """
    Make D-09 and D-10 have the exact same July closed margin
    by appending one adjustment load for D-10.
    Ranking must show a shared place.
    """
    from datetime import datetime as dt

    def july_margin(dispatcher_id: str) -> float:
        total = 0.0
        for load in loads:
            if load["status"] != "delivered" or not load["deliveredAt"]:
                continue
            delivered = dt.fromisoformat(load["deliveredAt"])
            # Rough UTC filter; engine uses Chicago. July 1 05:00Z .. Aug 1 05:00Z
            if not (dt(2026, 7, 1, 5, tzinfo=timezone.utc) <= delivered < dt(2026, 8, 1, 5, tzinfo=timezone.utc)):
                continue
            if load["closedBy"] != dispatcher_id:
                continue
            total += load["customerRate"] - load["driverPay"]
        return round_money(total)

    m9 = july_margin("D-09")
    m10 = july_margin("D-10")
    delta = round_money(m9 - m10)
    # One delivered load whose margin equals the gap
    customer = 2000.00
    driver = round_money(customer - delta)
    loads.append(
        make_load(
            "L-TIE-ADJUST",
            "delivered",
            "D-10",
            "D-10",
            datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 26, 10, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 27, 18, 0, tzinfo=timezone.utc),
            customer,
            driver,
            300,
            "Raleigh, NC",
            "Savannah, GA",
            ["forced_tie"],
        )
    )
    return "D-09", "D-10"


def generate() -> None:
    rng = random.Random(SEED)

    dispatchers = []
    for did, name, hired, status, terminated, tz, _skill in DISPATCHER_DEFS:
        rec = {
            "id": did,
            "name": name,
            "hiredAt": hired,
            "status": status,
            "timezone": tz,
        }
        if terminated:
            rec["terminatedAt"] = terminated
        dispatchers.append(rec)

    skill = {row[0]: row[6] for row in DISPATCHER_DEFS}

    loads: list[dict] = []
    events: list[dict] = []
    seq = 10000

    plant_edge_cases(loads, events, rng)
    planted_ids = {load["id"] for load in loads}

    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    end = datetime(2026, 8, 14, 18, 0, tzinfo=timezone.utc)

    # ~1200 organic loads across May–mid August
    target = 1180
    for _ in range(target):
        seq += 1
        load_id = f"L-{seq}"
        booked_at = start + timedelta(
            seconds=rng.randint(0, int((end - start).total_seconds()) - 86400)
        )
        pool = active_dispatchers_on(booked_at, dispatchers)
        if not pool:
            continue
        weights = [skill[d["id"]] for d in pool]
        booker = rng.choices(pool, weights=weights, k=1)[0]
        closer = booker

        # ~9% handoffs among delivered work
        if rng.random() < 0.09:
            others = [d for d in pool if d["id"] != booker["id"]]
            if others:
                closer = rng.choice(others)

        origin, dest, miles = lane(rng)
        quality = 0.92 + skill[booker["id"]] * 0.08
        customer, driver = rate_for(miles, rng, quality)

        roll = rng.random()
        # More in-progress toward "now"
        age_days = (end - booked_at).days
        if booked_at >= datetime(2026, 8, 10, tzinfo=timezone.utc):
            # recent: mix of open statuses for Live
            if roll < 0.18:
                status = "cancelled"
            elif roll < 0.40:
                status = "booked"
            elif roll < 0.62:
                status = "assigned"
            elif roll < 0.82:
                status = "picked_up"
            else:
                status = "delivered"
        elif age_days < 4:
            status = rng.choice(["booked", "assigned", "picked_up", "delivered"])
        else:
            if roll < 0.08:
                status = "cancelled"
            elif roll < 0.11:
                status = "assigned"
            elif roll < 0.14:
                status = "picked_up"
            else:
                status = "delivered"

        pickup_at = None
        delivered_at = None
        if status == "cancelled":
            closed_by = None
        else:
            closed_by = closer["id"]
            pickup_at = booked_at + timedelta(hours=rng.randint(8, 40))
            if status in ("picked_up", "delivered"):
                if status == "delivered":
                    delivered_at = pickup_at + timedelta(hours=rng.randint(10, 72))
                    # keep deliveries inside the dataset window
                    if delivered_at > end:
                        delivered_at = end - timedelta(minutes=rng.randint(5, 180))
                        if delivered_at <= pickup_at:
                            status = "picked_up"
                            delivered_at = None

        # Sprinkle negative margins
        if status == "delivered" and rng.random() < 0.035:
            driver = round_money(customer + rng.uniform(40, 280))

        tags = ["organic"]
        if booker["id"] != (closed_by or booker["id"]):
            tags.append("handoff")

        load = make_load(
            load_id,
            status,
            booker["id"],
            closed_by,
            booked_at,
            pickup_at,
            delivered_at,
            customer,
            driver,
            miles,
            origin,
            dest,
            tags,
        )
        loads.append(load)
        events.extend(build_events_for_load(load, rng))

    tie_a, tie_b = force_july_tie(loads)
    # events for the tie load
    tie_load = next(load for load in loads if load["id"] == "L-TIE-ADJUST")
    events.extend(build_events_for_load(tie_load, rng))

    events.sort(key=lambda e: e["at"])
    loads.sort(key=lambda load: load["bookedAt"])

    delivered = sum(1 for load in loads if load["status"] == "delivered")
    cancelled = sum(1 for load in loads if load["status"] == "cancelled")

    write_json(OUT_DIR / "dispatchers.json", dispatchers)
    write_json(OUT_DIR / "loads.json", loads)
    write_json(OUT_DIR / "events.json", events)

    meta = {
        "seed": SEED,
        "companyTimezone": COMPANY_TZ,
        "dispatchers": len(dispatchers),
        "loads": len(loads),
        "events": len(events),
        "delivered": delivered,
        "cancelled": cancelled,
        "plantedLoadIds": sorted(planted_ids | {"L-TIE-ADJUST"}),
        "forcedTie": [tie_a, tie_b],
        "window": {"start": iso(start), "end": iso(end)},
    }
    write_json(OUT_DIR / "meta.json", meta)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    generate()
