const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface DashboardStats {
  current_balance: number;
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
    selection: string;
    model_prob: number;
    fair_odds: number;
    best_bookmaker: string;
    best_odds: number;
    ev_percent: number;
    recommended_stake: number;
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
  placed_at: string;
  resolved_at?: string;
}

export async function fetchStats(): Promise<DashboardStats> {
  const res = await fetch(`${API_BASE_URL}/dashboard/stats`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch dashboard stats");
  return res.json();
}

export async function fetchMatches(league?: string): Promise<MatchItem[]> {
  const url = league ? `${API_BASE_URL}/matches/?league=${encodeURIComponent(league)}` : `${API_BASE_URL}/matches/`;
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

export async function fetchValueBets(minEv = 3.0, league?: string): Promise<ValueBetItem[]> {
  let url = `${API_BASE_URL}/predictions/value-bets?min_ev=${minEv}`;
  if (league) url += `&league=${encodeURIComponent(league)}`;
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
