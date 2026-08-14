"use client";

import { useEffect, useRef, useState } from "react";
import { chicagoTime } from "@/lib/format";
import type { LiveEvent } from "@/lib/types";

export default function LivePage() {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [mode, setMode] = useState<"idle" | "replay" | "live">("idle");
  const [status, setStatus] = useState("Connecting…");
  const seen = useRef(new Set<string>());

  useEffect(() => {
    let es: EventSource | null = null;
    let cancelled = false;

    fetch("/api/events?limit=80")
      .then((r) => r.json())
      .then((payload) => {
        if (cancelled) return;
        const initial: LiveEvent[] = payload.events.slice().reverse();
        initial.forEach((e) => seen.current.add(e.id));
        setEvents(initial);
        setStatus("Tape loaded. Replaying Aug 13–14 on a 1.6s clock.");
        setMode("replay");
      })
      .catch(() => setStatus("API unreachable"));

    // Hit the API host directly. Next.js rewrites buffer SSE.
    const apiHost = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
    es = new EventSource(`${apiHost}/api/live/stream`);
    es.addEventListener("load", (msg) => {
      const event = JSON.parse((msg as MessageEvent).data) as LiveEvent;
      if (seen.current.has(event.id)) return;
      seen.current.add(event.id);
      setEvents((prev) => [event, ...prev].slice(0, 120));
      setMode("replay");
    });
    es.addEventListener("ping", () => setMode("live"));
    es.onerror = () => setStatus("Stream dropped — showing last snapshot. Refresh to replay.");

    return () => {
      cancelled = true;
      es?.close();
    };
  }, []);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>
            <span className="live-dot" />
            Load tape
          </h1>
          <p>
            Dataset is synthetic and frozen at 14 Aug 2026 18:00 UTC. This screen
            does not invent new freight — it replays the last two days over SSE so
            the board moves without a reload.
          </p>
        </div>
      </div>
      <p className="muted">
        {status} · {mode === "live" ? "replay finished, heartbeat only" : mode}
      </p>
      <div className="feed" style={{ marginTop: 16 }}>
        {events.map((event) => (
          <article key={event.id} className={`event ${event.type}`}>
            <span className="t">{chicagoTime(event.at)} CT</span>
            <span className="kind">{event.type.replace("_", " ")}</span>
            <span>
              <b>{event.loadId}</b>
              <span className="muted"> · {event.dispatcherName}</span>
            </span>
            <span className="muted">{event.dispatcherId}</span>
          </article>
        ))}
      </div>
    </>
  );
}
