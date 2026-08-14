"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { initials, money, n, rpm } from "@/lib/format";
import type { LeaderboardResponse, LeaderboardRow } from "@/lib/types";

type SortKey = "rank" | "margin" | "loadsClosed" | "marginPerActiveDay" | "rpm" | "avgMargin";

export default function LeaderboardPage() {
  const period = useSearchParams().get("period") || undefined;
  const q = period ? `?period=${period}` : "";
  const [data, setData] = useState<LeaderboardResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>("rank");
  const [fairness, setFairness] = useState(false);

  useEffect(() => {
    api.leaderboard(period).then(setData).catch((e) => setErr(String(e)));
  }, [period]);

  const rows = useMemo(() => {
    if (!data) return [];
    const copy = [...data.rows];
    const key: SortKey = fairness ? "marginPerActiveDay" : sort;
    if (key === "rank") return copy;
    copy.sort((a, b) => (b[key] as number) - (a[key] as number));
    return copy;
  }, [data, sort, fairness]);

  if (err) return <p className="muted">{err}. Is the API running on :8000?</p>;
  if (!data) return <p className="muted">Loading ranking…</p>;

  const maxMargin = Math.max(...data.rows.map((r) => r.margin), 1);
  const maxPace = Math.max(...data.rows.map((r) => r.marginPerActiveDay), 1);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>{data.period.label} ranking</h1>
          <p>
            Official sort is closed margin. Credit goes to whoever closed the load,
            in the month it was delivered, on the Chicago clock.
          </p>
        </div>
      </div>

      <div className="kpis">
        <div className="kpi">
          <span>Company margin</span>
          <b>{money(data.company.margin)}</b>
          <em>{n(data.company.loads)} delivered loads</em>
        </div>
        <div className="kpi">
          <span>Ranked dispatchers</span>
          <b>{data.company.dispatchersRanked}</b>
          <em>active at least one day, or with a close</em>
        </div>
        <div className="kpi">
          <span>Network RPM</span>
          <b>{rpm(data.company.rpm)}</b>
          <em>{n(data.company.miles)} miles</em>
        </div>
        <div className="kpi">
          <span>Not counted</span>
          <b>{data.company.excludedCount}</b>
          <em>open, cancelled, or unattributed</em>
        </div>
      </div>

      <div className="toolbar">
        <button className={!fairness && sort === "rank" ? "on" : ""} onClick={() => { setFairness(false); setSort("rank"); }}>
          Bonus rank
        </button>
        <button className={!fairness && sort === "loadsClosed" ? "on" : ""} onClick={() => { setFairness(false); setSort("loadsClosed"); }}>
          Loads
        </button>
        <button className={!fairness && sort === "rpm" ? "on" : ""} onClick={() => { setFairness(false); setSort("rpm"); }}>
          RPM
        </button>
        <button className={!fairness && sort === "avgMargin" ? "on" : ""} onClick={() => { setFairness(false); setSort("avgMargin"); }}>
          Avg / load
        </button>
        <button className={fairness ? "on" : ""} onClick={() => setFairness((v) => !v)}>
          Fairness: $ / day
        </button>
      </div>

      {fairness && (
        <div className="warn-banner">
          This is a pace view for people who started mid-month. It is not the bonus
          ranking — two fat days would game it. Official money still uses total margin.
        </div>
      )}

      <div className="board">
        {rows.map((row) => (
          <BoardRow
            key={row.dispatcher.id}
            row={row}
            href={`/dispatchers/${row.dispatcher.id}${q}`}
            max={fairness ? maxPace : maxMargin}
            value={fairness ? row.marginPerActiveDay : row.margin}
          />
        ))}
      </div>

      <ul className="notes">
        {data.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>

      <section className="trust">
        <h2>What did not count</h2>
        <p>
          Bonuses only move when a load is delivered and has a closer. Everything
          else is listed so a dispatcher can challenge the number.
        </p>
        <div className="excl">
          {data.excluded.summary.map((item) => (
            <div key={item.reason}>
              <small className="muted">{item.label}</small>
              <div><b>{item.count}</b> loads</div>
              <div className="muted">{money(item.margin)} face margin</div>
            </div>
          ))}
        </div>
        <div className="samples">
          {data.excluded.samples.slice(0, 8).map((s) => (
            <div key={s.loadId}>
              <code>{s.loadId}</code> · {s.reason} · {s.detail}
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

function BoardRow({
  row,
  href,
  max,
  value,
}: {
  row: LeaderboardRow;
  href: string;
  max: number;
  value: number;
}) {
  const deltaCls =
    row.rankDelta == null ? "flat" : row.rankDelta > 0 ? "up" : row.rankDelta < 0 ? "down" : "flat";
  const top = row.rank === 1 ? "top1" : row.rank === 2 ? "top2" : row.rank === 3 ? "top3" : "";
  return (
    <Link href={href} className={`row ${top}`}>
      <div>
        <div className="rank">#{row.rank}</div>
        <div className={`delta ${deltaCls}`}>
          {row.rankDeltaLabel === "new" ? "new" : row.rankDeltaLabel}
        </div>
      </div>
      <div>
        <div className="who">
          <span className="avatar">{initials(row.dispatcher.name)}</span>
          <div>
            <strong>{row.dispatcher.name}</strong>
            <small>
              {row.dispatcher.id} · {row.dispatcher.timezone.replace("America/", "")}
            </small>
            <div className="badges">
              {row.tied && <span className="badge tie">tied</span>}
              {row.newHire && <span className="badge new">new hire</span>}
              {row.partialPeriod && (
                <span className="badge new">
                  {row.daysActive}/{row.periodDays} days
                </span>
              )}
              {row.dispatcher.status === "terminated" && <span className="badge gone">terminated</span>}
              {row.lossLoads > 0 && <span className="badge loss">{row.lossLoads} loss</span>}
              {row.handoffsIn > 0 && <span className="badge">{row.handoffsIn} taken</span>}
            </div>
          </div>
        </div>
        <div className="bar-wrap">
          <div className="bar" style={{ width: `${Math.max(2, (Math.max(value, 0) / max) * 100)}%` }} />
        </div>
      </div>
      <div className="num">
        {money(row.margin)}
        <small>closed $</small>
      </div>
      <div className="num">
        {row.loadsClosed}
        <small>loads</small>
      </div>
      <div className="num">
        {money(row.marginPerActiveDay)}
        <small>$ / day</small>
      </div>
      <div className="num">
        {rpm(row.rpm)}
        <small>avg {money(row.avgMargin)}</small>
      </div>
    </Link>
  );
}
