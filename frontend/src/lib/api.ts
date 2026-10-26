const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

export interface DashboardStats {
  current_balance: number;
  total_equity?: number;
  active_stakes?: number;
  initial_balance: number;
  total_staked: number;
  total_pnl: number;
  roi_percent: number;
  win_rate_percent: number;
  greens: number;
  reds: number;
  voids: number;
  total_bets: number;
  max_drawdown_percent: number;
  history: Array<{
    timestamp: string;
    balance: number;
    delta: number;
    description: string;
  }>;
}

export interface MatchItem {
  id: number;
  home_team: string;
  away_team: string;
  league: string;
  kickoff: string;
  status: string;
  home_score?: number;
  away_score?: number;
  odds: Array<{
    bookmaker: string;
    market_type: string;
    selection: string;
    odds: number;
  }>;
  predictions: Array<{
    id: number;
    market_type?: string;
    selection: string;
    model_prob: number;
    fair_odds: number;
    best_bookmaker: string;
    best_odds: number;
    ev_percent: number;
    recommended_stake: number;
    confidence?: string;
    reasoning?: string;
  }>;
}

export interface ValueBetItem {
  id: number;
  match_id: number;
  home_team: string;
  away_team: string;
  league: string;
  kickoff: string;
  market_type: string;
  selection: string;
  model_prob: number;
  fair_odds: number;
  best_bookmaker: string;
  best_odds: number;
  ev_percent: number;
  kelly_stake_percent: number;
  recommended_stake: number;
  confidence?: string;
  reasoning?: string;
}

export interface CuratedMultiple {
  legs_count: number;
  total_odds: number;
  fair_odds: number;
  combined_ev_percent: number;
  combined_prob_percent: number;
  recommended_stake: number;
  potential_payout: number;
  legs: Array<{
    match: string;
    league: string;
    market: string;
    selection: string;
    bookmaker: string;
    odds: number;
    confidence: string;
    reasoning: string;
  }>;
}

export interface PaperBetItem {
  id: number;
  match_id: number;
  home_team: string;
  away_team: string;
  league: string;
  bookmaker: string;
  market_type: string;
  selection: string;
  odds: number;
  stake: number;
  potential_payout: number;
  status: "PENDING" | "GREEN" | "RED" | "VOID";
  profit_loss: number;
  confidence?: string;
  reasoning?: string;
  home_score?: number | null;
  away_score?: number | null;
  match_status?: string;
  placed_at: string;
  resolved_at?: string;
}

export interface SystemSettings {
  auto_bet_enabled: boolean;
  cron_interval_minutes: number;
  discord_configured: boolean;
  discord_webhook_preview?: string;
  min_ev_threshold: number;
  kelly_fraction: number;
  max_bet_percentage: number;
  target_leagues: string[];
}

export async function fetchStats(): Promise<DashboardStats> {
  const res = await fetch(`${API_BASE_URL}/dashboard/stats`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch dashboard stats");
  return res.json();
}

export async function fetchMatches(league?: string, todayOnly = false): Promise<MatchItem[]> {
  let url = `${API_BASE_URL}/matches`;
  const params = new URLSearchParams();
  if (league) params.append("league", league);
  if (todayOnly) params.append("today_only", "true");
  const qs = params.toString();
  if (qs) url += `?${qs}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch matches");
  return res.json();
}

export async function syncMatches(league?: string): Promise<{ message: string }> {
  const url = league ? `${API_BASE_URL}/matches/sync?league=${encodeURIComponent(league)}` : `${API_BASE_URL}/matches/sync`;
  const res = await fetch(url, { method: "POST" });
  if (!res.ok) throw new Error("Failed to trigger sync");
  return res.json();
}

export async function checkLiveScores(): Promise<{ message: string; settled_bets_count: number }> {
  const res = await fetch(`${API_BASE_URL}/matches/check-live-scores`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to check live scores");
  return res.json();
}

export async function fetchValueBets(
  minEv = 3.5,
  league?: string,
  todayOnly = true,
  targetDate?: string
): Promise<ValueBetItem[]> {
  let url = `${API_BASE_URL}/predictions/value-bets?min_ev=${minEv}&today_only=${todayOnly}`;
  if (league) url += `&league=${encodeURIComponent(league)}`;
  if (targetDate) url += `&target_date=${encodeURIComponent(targetDate)}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch value bets");
  return res.json();
}

export async function fetchPaperBets(status?: string): Promise<PaperBetItem[]> {
  const url = status ? `${API_BASE_URL}/paper-trading/bets?status=${status}` : `${API_BASE_URL}/paper-trading/bets`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch paper bets");
  return res.json();
}

export async function placePaperBet(data: {
  match_id: number;
  bookmaker: string;
  market_type?: string;
  selection: string;
  odds: number;
  stake: number;
  prediction_id?: number;
}): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/paper-trading/bet`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to place bet");
  }
  return res.json();
}

export async function resolveMatch(match_id: number, home_score: number, away_score: number): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/paper-trading/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ match_id, home_score, away_score }),
  });
  if (!res.ok) throw new Error("Failed to resolve match");
  return res.json();
}

export async function resetBankroll(initial_balance = 1000): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/paper-trading/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ initial_balance }),
  });
  if (!res.ok) throw new Error("Failed to reset bankroll");
  return res.json();
}

export async function fetchSettings(): Promise<SystemSettings> {
  const res = await fetch(`${API_BASE_URL}/settings`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch settings");
  return res.json();
}

export async function updateSettings(data: {
  auto_bet_enabled?: boolean;
  discord_webhook_url?: string;
  min_ev_threshold?: number;
}): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update settings");
  return res.json();
}

export async function testDiscordWebhook(webhook_url?: string): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/settings/test-discord`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ webhook_url }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Discord webhook test failed");
  }
  return res.json();
}

export async function triggerCronCycleNow(): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/settings/run-cycle`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to run cron cycle");
  return res.json();
}

export async function fetchCuratedMultiple(todayOnly = true): Promise<CuratedMultiple | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/predictions/curated-multiple?today_only=${todayOnly}`, { cache: "no-store" });
    if (!res.ok) return null;
    const data = await res.json();
    return data?.legs_count ? data : null;
  } catch {
    return null;
  }
}
