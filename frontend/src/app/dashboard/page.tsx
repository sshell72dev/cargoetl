"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { money, n } from "@/lib/format";
import type { DashboardResponse } from "@/lib/types";

export default function DashboardPage() {
  const period = useSearchParams().get("period") || undefined;
  const q = period ? `?period=${period}` : "";
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.dashboard(period).then(setData).catch((e) => setErr(String(e)));
  }, [period]);

  if (err) return <p className="muted">{err}</p>;
  if (!data) return <p className="muted">Loading desk…</p>;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Desk snapshot · {data.period.label}</h1>
          <p>
            What the company actually banked this month, who moved, and which
            numbers are still arguments waiting to happen.
          </p>
        </div>
      </div>

      <div className="kpis">
        <div className="kpi">
          <span>Closed margin</span>
          <b>{money(data.company.margin)}</b>
          <em className={data.company.marginDelta >= 0 ? "pos" : "neg"}>
            {money(data.company.marginDelta, true)} vs prior month
          </em>
        </div>
        <div className="kpi">
          <span>Delivered loads</span>
          <b>{n(data.company.loads)}</b>
          <em>
            {data.company.loadsDelta >= 0 ? "+" : ""}
            {data.company.loadsDelta} vs {n(data.company.previousLoads)}
          </em>
        </div>
        <div className="kpi">
          <span>Left on the table</span>
          <b>{n(data.company.excludedCount)}</b>
          <em>not in the bonus pool</em>
        </div>
        <div className="kpi">
          <span>Network RPM</span>
          <b>${data.company.rpm.toFixed(2)}</b>
          <em>margin per mile</em>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <h2>Top 3 closers</h2>
          <div className="podium">
            {data.top3.map((row) => (
              <Link key={row.dispatcher.id} href={`/dispatchers/${row.dispatcher.id}${q}`}>
                <span>
                  #{row.rank} {row.dispatcher.name}
                  {row.tied ? " · tied" : ""}
                </span>
                <span className="num">{money(row.margin)}</span>
              </Link>
            ))}
          </div>
        </div>
        <div className="card">
          <h2>What moved</h2>
          {data.biggestClimber && (
            <p>
              Biggest climb: <b>{data.biggestClimber.dispatcher.name}</b>{" "}
              <span className="pos">{data.biggestClimber.rankDeltaLabel}</span> to #
              {data.biggestClimber.rank}
            </p>
          )}
          {data.biggestDrop && (
            <p>
              Biggest drop: <b>{data.biggestDrop.dispatcher.name}</b>{" "}
              <span className="neg">{data.biggestDrop.rankDeltaLabel}</span> to #
              {data.biggestDrop.rank}
            </p>
          )}
          {data.newHires.length > 0 && (
            <p>
              New this month:{" "}
              {data.newHires.map((r) => r.dispatcher.name).join(", ")}. Ranked on
              total margin, flagged as partial.
            </p>
          )}
        </div>
        <div className="card">
          <h2>Loss loads still count</h2>
          <p className="muted">
            Negative margin is real money. Hiding it would inflate bonuses.
          </p>
          {data.lossLeaders.map((row) => (
            <p key={row.dispatcher.id}>
              {row.dispatcher.name} · {row.lossLoads} underwater close
              {row.lossLoads === 1 ? "" : "s"}
            </p>
          ))}
        </div>
        <div className="card">
          <h2>Excluded from ranking</h2>
          {data.excluded.map((item) => (
            <p key={item.reason}>
              <b>{item.count}</b> {item.label}
            </p>
          ))}
        </div>
      </div>

      <ul className="notes">
        {data.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
        <li>
          Attribution: closer. Period field: deliveredAt. Timezone: America/Chicago.
        </li>
      </ul>
    </>
  );
}
