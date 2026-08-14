"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { money } from "@/lib/format";
import type { LeaderboardRow } from "@/lib/types";

type Person = {
  id: string;
  name: string;
  status: string;
  hiredAt: string;
  terminatedAt?: string | null;
  timezone: string;
  row: LeaderboardRow | null;
};

export default function DispatchersPage() {
  const period = useSearchParams().get("period") || undefined;
  const q = period ? `?period=${period}` : "";
  const [people, setPeople] = useState<Person[]>([]);
  const [query, setQuery] = useState("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.dispatchers(period)
      .then((d) => setPeople(d.dispatchers as Person[]))
      .catch((e) => setErr(String(e)));
  }, [period]);

  const filtered = useMemo(() => {
    const qstr = query.toLowerCase();
    return people.filter(
      (p) =>
        p.name.toLowerCase().includes(qstr) || p.id.toLowerCase().includes(qstr)
    );
  }, [people, query]);

  if (err) return <p className="muted">{err}</p>;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Roster</h1>
          <p>Open a card for the loads behind the number — counted and excluded.</p>
        </div>
        <input
          className="search"
          placeholder="Search name or id"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            <th>Dispatcher</th>
            <th>Status</th>
            <th>Hired</th>
            <th>Closed $</th>
            <th>Loads</th>
            <th>$ / day</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((p) => (
            <tr key={p.id}>
              <td className="num">{p.row ? `#${p.row.rank}` : "—"}</td>
              <td>
                <Link href={`/dispatchers/${p.id}${q}`}>
                  <b>{p.name}</b>
                  <div className="muted">{p.id} · {p.timezone.replace("America/", "")}</div>
                </Link>
              </td>
              <td>{p.status}</td>
              <td>{p.hiredAt}</td>
              <td className="num">{p.row ? money(p.row.margin) : "—"}</td>
              <td className="num">{p.row?.loadsClosed ?? "—"}</td>
              <td className="num">{p.row ? money(p.row.marginPerActiveDay) : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
