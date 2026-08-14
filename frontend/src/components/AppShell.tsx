"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

const NAV = [
  { href: "/", label: "Leaderboard" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/live", label: "Live" },
  { href: "/dispatchers", label: "Dispatchers" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const search = useSearchParams();
  const router = useRouter();
  const period = search.get("period") || "";
  const [periods, setPeriods] = useState<string[]>([]);
  const [def, setDef] = useState("2026-07");

  useEffect(() => {
    fetch(`${API_BASE}/api/periods`)
      .then((r) => r.json())
      .then((data) => {
        setPeriods(data.periods);
        setDef(data.default);
      })
      .catch(() => undefined);
  }, []);

  function setPeriod(next: string) {
    const params = new URLSearchParams(search.toString());
    if (!next || next === def) params.delete("period");
    else params.set("period", next);
    const q = params.toString();
    router.push(q ? `${pathname}?${q}` : pathname);
  }

  const activePeriod = period || def;
  const q = period ? `?period=${period}` : "";

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="mark">CE</span>
          <div>
            <strong>CargoETL</strong>
            <em>Dispatcher board</em>
          </div>
        </div>
        <nav>
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={`${item.href}${q}`}
              className={pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href)) ? "on" : ""}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <label className="period">
          <span>Period</span>
          <select value={activePeriod} onChange={(e) => setPeriod(e.target.value)}>
            {(periods.length ? periods : [activePeriod]).map((p) => (
              <option key={p} value={p}>
                {p}
                {p === def ? " · last full month" : ""}
              </option>
            ))}
          </select>
        </label>
      </header>
      <p className="clock-note">
        Money months close on the company clock: <b>America/Chicago</b>. Individual
        dispatcher timezones are shown, not used for ranking.
      </p>
      <main>{children}</main>
    </div>
  );
}
