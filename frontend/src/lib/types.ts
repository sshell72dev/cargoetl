export type Dispatcher = {
  id: string;
  name: string;
  status: "active" | "terminated";
  hiredAt: string;
  terminatedAt?: string | null;
  timezone: string;
};

export type LeaderboardRow = {
  rank: number;
  previousRank: number | null;
  rankDelta: number | null;
  rankDeltaLabel: string;
  dispatcher: Dispatcher;
  margin: number;
  loadsClosed: number;
  avgMargin: number;
  rpm: number;
  miles: number;
  marginPerActiveDay: number;
  daysActive: number;
  periodDays: number;
  partialPeriod: boolean;
  newHire: boolean;
  handoffsIn: number;
  handoffsOut: number;
  lossLoads: number;
  bookedLoads: number;
  bookedMargin: number;
  tied: boolean;
};

export type ExclusionSummary = {
  reason: string;
  label: string;
  count: number;
  margin: number;
};

export type LeaderboardResponse = {
  period: {
    id: string;
    label: string;
    start: string;
    end: string;
    timezone: string;
    previousPeriod: string;
  };
  rules: {
    attribution: string;
    periodField: string;
    timezone: string;
    includeNegativeMargin: boolean;
    ranking: string;
  };
  company: {
    margin: number;
    loads: number;
    miles: number;
    rpm: number;
    excludedCount: number;
    dispatchersRanked: number;
  };
  rows: LeaderboardRow[];
  excluded: {
    summary: ExclusionSummary[];
    samples: Array<{
      loadId: string;
      reason: string;
      detail: string;
      bookedBy?: string;
      closedBy?: string | null;
      margin: number;
    }>;
    total: number;
  };
  notes: string[];
};

export type DashboardResponse = {
  period: LeaderboardResponse["period"];
  company: LeaderboardResponse["company"] & {
    previousMargin: number;
    marginDelta: number;
    previousLoads: number;
    loadsDelta: number;
  };
  top3: LeaderboardRow[];
  biggestClimber: LeaderboardRow | null;
  biggestDrop: LeaderboardRow | null;
  newHires: LeaderboardRow[];
  partialPeriod: LeaderboardRow[];
  lossLeaders: LeaderboardRow[];
  notes: string[];
  excluded: ExclusionSummary[];
  rules: LeaderboardResponse["rules"];
};

export type LoadRow = {
  id: string;
  status: string;
  origin: string;
  destination: string;
  miles: number;
  customerRate: number;
  driverPay: number;
  margin: number;
  bookedBy: string;
  closedBy: string | null;
  bookedAt: string;
  deliveredAt: string | null;
  counted: boolean;
  excludeReason: string | null;
  handoff: boolean;
};

export type DispatcherDetail = {
  dispatcher: Dispatcher;
  row: LeaderboardRow | null;
  period: LeaderboardResponse["period"];
  loads: LoadRow[];
  countedLoads: LoadRow[];
  excludedLoads: LoadRow[];
};

export type LiveEvent = {
  id: string;
  loadId: string;
  type: string;
  at: string;
  dispatcherId: string;
  dispatcherName: string;
};
