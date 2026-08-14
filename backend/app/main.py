from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from . import data
from .leaderboard import (
    available_periods,
    build_dashboard,
    build_leaderboard,
    default_period,
    dispatcher_detail,
    previous_period,
)

DEMO_NOW = datetime(2026, 8, 14, 18, 0, tzinfo=timezone.utc)

app = FastAPI(title="CargoETL Dispatcher Board", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def resolve_period(period: Optional[str]) -> str:
    periods = available_periods(data.loads(), DEMO_NOW)
    chosen = period or default_period(DEMO_NOW)
    if chosen not in periods:
        # still allow a well-formed YYYY-MM even if empty
        if len(chosen) != 7 or chosen[4] != "-":
            raise HTTPException(400, f"Unknown period '{chosen}'")
    return chosen


def leaderboard_for(period: Optional[str]) -> dict:
    return build_leaderboard(data.dispatchers(), data.loads(), resolve_period(period))


@app.get("/api/health")
def health():
    return {"ok": True, "now": DEMO_NOW.isoformat(), "defaultPeriod": default_period(DEMO_NOW)}


@app.get("/api/periods")
def periods():
    return {
        "default": default_period(DEMO_NOW),
        "periods": available_periods(data.loads(), DEMO_NOW),
        "timezone": "America/Chicago",
        "now": DEMO_NOW.isoformat(),
    }


@app.get("/api/leaderboard")
def leaderboard(period: Optional[str] = Query(default=None)):
    return leaderboard_for(period)


@app.get("/api/dashboard")
def dashboard(period: Optional[str] = Query(default=None)):
    current = leaderboard_for(period)
    previous = build_leaderboard(
        data.dispatchers(),
        data.loads(),
        previous_period(current["period"]["id"]),
    )
    return build_dashboard(current, previous)


@app.get("/api/dispatchers")
def list_dispatchers(period: Optional[str] = Query(default=None)):
    board = leaderboard_for(period)
    by_id = {row["dispatcher"]["id"]: row for row in board["rows"]}
    people = []
    for dispatcher in data.dispatchers():
        people.append(
            {
                **dispatcher,
                "row": by_id.get(dispatcher["id"]),
            }
        )
    people.sort(key=lambda item: (item["row"] or {}).get("rank") or 999)
    return {"period": board["period"], "dispatchers": people}


@app.get("/api/dispatchers/{dispatcher_id}")
def get_dispatcher(dispatcher_id: str, period: Optional[str] = Query(default=None)):
    board = leaderboard_for(period)
    detail = dispatcher_detail(dispatcher_id, data.dispatchers(), data.loads(), board)
    if detail is None:
        raise HTTPException(404, "Dispatcher not found")
    return detail


@app.get("/api/events")
def list_events(
    after: Optional[str] = Query(default=None),
    limit: int = Query(default=80, ge=1, le=300),
    load_id: Optional[str] = Query(default=None, alias="loadId"),
):
    names = {d["id"]: d["name"] for d in data.dispatchers()}
    items = data.events()
    if load_id:
        items = [e for e in items if e["loadId"] == load_id]
    if after:
        items = [e for e in items if e["at"] > after or (e["at"] == after and e["id"] > after)]
    else:
        items = items[-limit:]
    items = items[:limit]
    enriched = []
    for event in items:
        enriched.append(
            {
                **event,
                "dispatcherName": names.get(event["dispatcherId"], event["dispatcherId"]),
            }
        )
    return {
        "now": DEMO_NOW.isoformat(),
        "events": enriched,
        "cursor": enriched[-1]["at"] if enriched else after,
    }


@app.get("/api/live/stream")
async def live_stream():
    """
    SSE replay of the latest events, then a heartbeat.
    The dataset is static, so this replays the tail of Aug 13–14 on a timer
    rather than inventing freight.
    """
    import asyncio
    import itertools
    import json

    names = {d["id"]: d["name"] for d in data.dispatchers()}
    tail = [e for e in data.events() if e["at"] >= "2026-08-13T00:00:00+00:00"][-60:]

    async def gen():
        yield "event: hello\ndata: {\"ok\": true}\n\n"
        for event in tail:
            payload = {**event, "dispatcherName": names.get(event["dispatcherId"], "")}
            yield f"event: load\ndata: {json.dumps(payload)}\n\n"
            await asyncio.sleep(1.6)
        for tick in itertools.count():
            yield f"event: ping\ndata: {{\"n\": {tick}}}\n\n"
            await asyncio.sleep(8)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
