"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { chicagoTime, money, moneyExact, n } from "@/lib/format";
import type { DispatcherDetail } from "@/lib/types";

export default function DispatcherCardPage() {
  const { id } = useParams<{ id: string }>();
  const period = useSearchParams().get("period") || undefined;
  const q = period ? `?period=${period}` : "";
  const [data, setData] = useState<DispatcherDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.dispatcher(id, period).then(setData).catch((e) => setErr(String(e)));
  }, [id, period]);

  if (err) return <p className="muted">{err}</p>;
  if (!data) return <p className="muted">Loading card…</p>;

  const row = data.row;

  return (
    <>
      <p className="muted">
        <Link href={`/dispatchers${q}`}>← Roster</Link>
      </p>
      <div className="page-head">
        <div>
          <h1>{data.dispatcher.name}</h1>
          <p>
            {data.dispatcher.id} · {data.dispatcher.status} · hired {data.dispatcher.hiredAt} ·{" "}
            {data.dispatcher.timezone}
            {data.dispatcher.terminatedAt ? ` · left ${data.dispatcher.terminatedAt}` : ""}
          </p>
        </div>
      </div>

      {row ? (
        <div className="kpis">
          <div className="kpi">
            <span>Place</span>
            <b>#{row.rank}</b>
            <em>
              {row.rankDeltaLabel === "new"
                ? "not in prior month"
                : `${row.rankDeltaLabel} vs ${data.period.previousPeriod}`}
            </em>
          </div>
          <div className="kpi">
            <span>Closed margin</span>
            <b>{money(row.margin)}</b>
            <em>{row.loadsClosed} delivered closes</em>
          </div>
          <div className="kpi">
            <span>$ / active day</span>
            <b>{money(row.marginPerActiveDay)}</b>
            <em>
              {row.daysActive} of {row.periodDays} days
            </em>
          </div>
          <div className="kpi">
            <span>Booked vs closed</span>
            <b>{money(row.bookedMargin)}</b>
            <em>
              {row.bookedLoads} booked · {row.handoffsIn} taken · {row.handoffsOut} handed off
            </em>
          </div>
        </div>
      ) : (
        <p className="warn-banner">No ranked activity in this period.</p>
      )}

      <div className="card" style={{ marginBottom: 16 }}>
        <h2>Counted toward bonus ({data.countedLoads.length})</h2>
        <LoadTable rows={data.countedLoads} />
      </div>
      <div className="card">
        <h2>Touched the period, not counted ({data.excludedLoads.length})</h2>
        <LoadTable rows={data.excludedLoads} />
      </div>
    </>
  );
}

function LoadTable({ rows }: { rows: DispatcherDetail["loads"] }) {
  if (!rows.length) return <p className="muted">None.</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>Load</th>
          <th>Lane</th>
          <th>Margin</th>
          <th>Booked</th>
          <th>Closed</th>
          <th>When</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {rows.map((load) => (
          <tr key={load.id}>
            <td>
              <code>{load.id}</code>
              <div className="muted">{load.status}</div>
            </td>
            <td>
              {load.origin} → {load.destination}
              <div className="muted">{n(load.miles)} mi</div>
            </td>
            <td className={load.margin < 0 ? "neg num" : "num"}>{moneyExact(load.margin)}</td>
            <td>{load.bookedBy}</td>
            <td>{load.closedBy || "—"}</td>
            <td className="muted">
              {load.deliveredAt ? chicagoTime(load.deliveredAt) : chicagoTime(load.bookedAt)} CT
            </td>
            <td>
              {load.handoff && <span className="badge">handoff</span>}
              {load.excludeReason && <span className="badge">{load.excludeReason.replaceAll("_", " ")}</span>}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
