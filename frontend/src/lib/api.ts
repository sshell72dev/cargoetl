import type {
  DashboardResponse,
  DispatcherDetail,
  LeaderboardResponse,
  LiveEvent,
} from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function periodQuery(period?: string) {
  return period ? `?period=${encodeURIComponent(period)}` : "";
}

export const api = {
  periods: () =>
    get<{ default: string; periods: string[]; timezone: string; now: string }>(
      "/api/periods"
    ),
  leaderboard: (period?: string) =>
    get<LeaderboardResponse>(`/api/leaderboard${periodQuery(period)}`),
  dashboard: (period?: string) =>
    get<DashboardResponse>(`/api/dashboard${periodQuery(period)}`),
  dispatchers: (period?: string) =>
    get<{
      period: LeaderboardResponse["period"];
      dispatchers: Array<
        DispatcherDetail["dispatcher"] & { row: LeaderboardResponse["rows"][0] | null }
      >;
    }>(`/api/dispatchers${periodQuery(period)}`),
  dispatcher: (id: string, period?: string) =>
    get<DispatcherDetail>(`/api/dispatchers/${id}${periodQuery(period)}`),
  events: (after?: string) =>
    get<{ now: string; events: LiveEvent[]; cursor: string | null }>(
      after ? `/api/events?after=${encodeURIComponent(after)}&limit=80` : "/api/events?limit=80"
    ),
};
