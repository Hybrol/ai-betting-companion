"use client";

import { useEffect, useState } from "react";
import {
  Wallet,
  TrendingUp,
  CheckCircle2,
  XCircle,
  Percent,
  RotateCcw,
  Sparkles,
  ArrowRight,
  Zap,
  Bell,
  Clock,
  Calendar,
  ShieldAlert,
  Layers
} from "lucide-react";
import Link from "next/link";
import StatCard from "@/components/StatCard";
import BankrollChart from "@/components/BankrollChart";
import BetModal from "@/components/BetModal";
import SettingsModal from "@/components/SettingsModal";
import { fetchStats, fetchValueBets, fetchSettings, fetchCuratedMultiple, resetBankroll, DashboardStats, ValueBetItem, SystemSettings, CuratedMultiple } from "@/lib/api";

function formatMatchDate(isoString?: string) {
  if (!isoString) return "";
  try {
    const d = new Date(isoString);
    const now = new Date();

    const isToday =
      d.getDate() === now.getDate() &&
      d.getMonth() === now.getMonth() &&
      d.getFullYear() === now.getFullYear();

    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const isTomorrow =
      d.getDate() === tomorrow.getDate() &&
      d.getMonth() === tomorrow.getMonth() &&
      d.getFullYear() === tomorrow.getFullYear();

    const timeStr = d.toLocaleTimeString("pt-PT", {
      hour: "2-digit",
      minute: "2-digit",
    });

    if (isToday) {
      return `Hoje às ${timeStr}`;
    }
    if (isTomorrow) {
      return `Amanhã às ${timeStr}`;
    }

    const dateStr = d.toLocaleDateString("pt-PT", {
      day: "numeric",
      month: "short",
    });
    return `${dateStr} às ${timeStr}`;
  } catch {
    return isoString;
  }
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [topValues, setTopValues] = useState<ValueBetItem[]>([]);
  const [curatedMultiple, setCuratedMultiple] = useState<CuratedMultiple | null>(null);
  const [sysSettings, setSysSettings] = useState<SystemSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedBet, setSelectedBet] = useState<ValueBetItem | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const loadData = async (isBackground = false) => {
    try {
      if (!isBackground) setLoading(true);
      const [s, v, set, mult] = await Promise.all([
        fetchStats(),
        fetchValueBets(3.5, undefined, true),
        fetchSettings(),
        fetchCuratedMultiple(true)
      ]);
      setStats(s);
      setTopValues(v.slice(0, 6));
      setSysSettings(set);
      setCuratedMultiple(mult);
    } catch (err) {
      console.error(err);
    } finally {
      if (!isBackground) setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Auto-refresh dashboard every 20 seconds
    const interval = setInterval(() => {
      loadData(true);
    }, 20000);
    return () => clearInterval(interval);
  }, []);

  const handleReset = async () => {
    if (confirm("Reset fictional bankroll back to 1,000.00 €? All previous paper bets will be cleared.")) {
      await resetBankroll(1000);
      loadData();
    }
  };

  return (
    <div className="space-y-8">
      {/* Hero Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              <span>30-min Auto Monitor Active</span>
            </span>
            <button
              onClick={() => setSettingsOpen(true)}
              className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center gap-1 transition"
            >
              <Zap className={`w-3 h-3 ${sysSettings?.auto_bet_enabled ? "text-emerald-400" : "text-slate-500"}`} />
              <span>Auto-Bet: {sysSettings?.auto_bet_enabled ? "ON" : "OFF"}</span>
            </button>
            <button
              onClick={() => setSettingsOpen(true)}
              className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center gap-1 transition"
            >
              <Bell className={`w-3 h-3 ${sysSettings?.discord_configured ? "text-indigo-400" : "text-slate-500"}`} />
              <span>Discord: {sysSettings?.discord_configured ? "Connected" : "Not Set"}</span>
            </button>
          </div>
          <h1 className="text-3xl font-black text-white tracking-tight">Paper-Trading Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time odds analysis for Solverde &bull; Betclic &bull; Betano with fictional bankroll simulation
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 transition border border-slate-700"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Bankroll</span>
          </button>
          <Link
            href="/value-bets"
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition shadow-lg shadow-emerald-600/20"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>View All +EV Bets</span>
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Virtual Bankroll"
          value={`${stats?.current_balance.toFixed(2) || "1,000.00"} €`}
          subtitle={`Initial: ${stats?.initial_balance || 1000} €`}
          icon={Wallet}
          color="emerald"
        />
        <StatCard
          title="Net Profit / Loss"
          value={`${(stats?.total_pnl || 0) >= 0 ? "+" : ""}${stats?.total_pnl.toFixed(2) || "0.00"} €`}
          subtitle={`ROI / Yield: ${(stats?.roi_percent || 0).toFixed(1)}%`}
          icon={TrendingUp}
          color={(stats?.total_pnl || 0) >= 0 ? "emerald" : "rose"}
        />
        <StatCard
          title="Greens vs Reds"
          value={`${stats?.greens || 0}W - ${stats?.reds || 0}L`}
          subtitle={`Hit Rate: ${(stats?.win_rate_percent || 0).toFixed(1)}%`}
          icon={CheckCircle2}
          color="blue"
        />
        <StatCard
          title="Active In-Play / Staked"
          value={`${((stats?.active_stakes ?? stats?.total_staked ?? 0)).toFixed(2)} €`}
          subtitle={`Max Drawdown: ${(stats?.max_drawdown_percent || 0).toFixed(1)}%`}
          icon={Percent}
          color="amber"
        />
      </div>

      {/* Bankroll Chart */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-sm backdrop-blur">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold text-white">Bankroll Growth & Evolution</h2>
            <p className="text-xs text-slate-400">Chronological fictional wallet balance over time</p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 border border-slate-700">
            {stats?.history?.length || 0} Events
          </span>
        </div>
        <BankrollChart
          history={stats?.history || []}
          initialBalance={stats?.initial_balance || 1000}
        />
      </div>

      {/* Curated Multiple Banner (if available) */}
      {curatedMultiple && (
        <div className="p-5 rounded-2xl bg-gradient-to-r from-purple-950/40 via-indigo-950/30 to-slate-900/60 border border-purple-500/30 shadow-lg backdrop-blur">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-2.5">
              <span className="p-2 rounded-xl bg-purple-500/20 text-purple-400 border border-purple-500/30">
                <Layers className="w-5 h-5" />
              </span>
              <div>
                <h3 className="text-base font-extrabold text-white flex items-center gap-2">
                  <span>Múltipla de Valor do Dia</span>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    {curatedMultiple.legs_count} Seleções SRIJ
                  </span>
                </h3>
                <p className="text-xs text-slate-400">
                  Combinação ótima com edge positivo (+{curatedMultiple.combined_ev_percent}% EV)
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 bg-slate-900/80 px-3 py-1.5 rounded-xl border border-purple-500/20 text-xs">
              <div>
                <span className="text-slate-400">Odd:</span> <strong className="text-purple-400">{curatedMultiple.total_odds.toFixed(2)}</strong>
              </div>
              <div className="h-4 w-px bg-slate-800" />
              <div>
                <span className="text-slate-400">Stake:</span> <strong className="text-emerald-400">{curatedMultiple.recommended_stake.toFixed(2)} €</strong>
              </div>
              <div className="h-4 w-px bg-slate-800" />
              <div>
                <span className="text-slate-400">Retorno:</span> <strong className="text-white">{curatedMultiple.potential_payout.toFixed(2)} €</strong>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
            {curatedMultiple.legs.map((leg, idx) => (
              <div key={idx} className="p-3 rounded-xl bg-slate-900/70 border border-slate-800 text-xs space-y-1.5">
                <div className="flex items-center justify-between gap-1">
                  <div className="font-bold text-white truncate">{leg.match}</div>
                  {leg.kickoff && (
                    <span className="flex items-center gap-1 text-[10px] font-semibold text-purple-300 bg-purple-500/10 px-1.5 py-0.5 rounded border border-purple-500/20 whitespace-nowrap">
                      <Clock className="w-2.5 h-2.5" />
                      <span>{formatMatchDate(leg.kickoff)}</span>
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-slate-400 flex items-center justify-between">
                  <span>{leg.market}: <strong className="text-emerald-400">{leg.selection} @ {leg.odds.toFixed(2)}</strong> ({leg.bookmaker})</span>
                  <span className="text-[10px] text-slate-500">{leg.league}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Value Bets Section */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-sm backdrop-blur">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-emerald-400" />
              <span>Value Bets de Hoje (+EV)</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Hoje
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Oportunidades com valor estatístico positivo (+EV) exclusivas para os jogos do dia de hoje
            </p>
          </div>
          <Link
            href="/value-bets"
            className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
          >
            <span>See all {topValues.length} opportunities</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {topValues.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-sm">
            No active value opportunities meeting minimum threshold. Click &quot;Sync Odds&quot; to refresh feeds.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-800/60 text-slate-400 uppercase font-bold text-[10px] tracking-wider">
                <tr>
                  <th className="py-3 px-4 rounded-l-xl">Match & League</th>
                  <th className="py-3 px-4">Selection</th>
                  <th className="py-3 px-4">Best Bookmaker</th>
                  <th className="py-3 px-4">Odds</th>
                  <th className="py-3 px-4">Fair Odds (Prob)</th>
                  <th className="py-3 px-4">Expected Value</th>
                  <th className="py-3 px-4">Kelly Rec.</th>
                  <th className="py-3 px-4 rounded-r-xl text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {topValues.map((v) => (
                  <tr key={v.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-white text-sm">
                        {v.home_team} vs {v.away_team}
                      </div>
                      <div className="text-[11px] text-slate-400 font-medium flex items-center gap-1.5 mt-0.5">
                        <span>{v.league}</span>
                        <span>&bull;</span>
                        <span className="flex items-center gap-1 text-emerald-400 font-semibold bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20 w-fit">
                          <Calendar className="w-3 h-3 text-emerald-400" />
                          <span>{formatMatchDate(v.kickoff)}</span>
                        </span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-bold text-white">
                      <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                        {v.selection}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="font-semibold text-emerald-400">{v.best_bookmaker}</span>
                    </td>
                    <td className="py-3.5 px-4 font-extrabold text-white text-sm">{v.best_odds.toFixed(2)}</td>
                    <td className="py-3.5 px-4">
                      <span className="text-slate-300">{v.fair_odds.toFixed(2)}</span>
                      <span className="text-slate-500 ml-1">({(v.model_prob * 100).toFixed(1)}%)</span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-1 rounded-md text-[11px] font-extrabold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                        +{v.ev_percent.toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-bold text-emerald-400">
                      {v.recommended_stake.toFixed(2)} €
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => setSelectedBet(v)}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition shadow-sm"
                      >
                        Simulate Bet
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Responsible Gaming Footer Note */}
      <div className="p-3.5 rounded-xl bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
        <ShieldAlert className="w-4 h-4 text-amber-500" />
        <span>Aposta sempre com responsabilidade. Proibido a menores de 18 anos (+18). Linha de Apoio SICAD: 1414.</span>
      </div>

      {selectedBet && (
        <BetModal
          isOpen={!!selectedBet}
          onClose={() => setSelectedBet(null)}
          onSuccess={loadData}
          matchId={selectedBet.match_id}
          matchTitle={`${selectedBet.home_team} vs ${selectedBet.away_team}`}
          bookmaker={selectedBet.best_bookmaker}
          selection={selectedBet.selection}
          odds={selectedBet.best_odds}
          recommendedStake={selectedBet.recommended_stake}
          predictionId={selectedBet.id}
        />
      )}

      {settingsOpen && (
        <SettingsModal
          isOpen={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          onSaved={loadData}
        />
      )}
    </div>
  );
}
