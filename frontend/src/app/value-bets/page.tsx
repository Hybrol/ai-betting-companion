"use client";

import { useEffect, useState } from "react";
import { Award, Filter, Sparkles, TrendingUp } from "lucide-react";
import BetModal from "@/components/BetModal";
import { fetchValueBets, ValueBetItem } from "@/lib/api";

const LEAGUES = [
  "All Leagues",
  "Liga Portugal",
  "Premier League",
  "La Liga",
  "Serie A",
  "Bundesliga",
  "Champions League",
];

export default function ValueBetsPage() {
  const [valueBets, setValueBets] = useState<ValueBetItem[]>([]);
  const [selectedLeague, setSelectedLeague] = useState("All Leagues");
  const [minEv, setMinEv] = useState(3.0);
  const [loading, setLoading] = useState(true);
  const [selectedBet, setSelectedBet] = useState<ValueBetItem | null>(null);

  const loadBets = async () => {
    try {
      setLoading(true);
      const leagueParam = selectedLeague === "All Leagues" ? undefined : selectedLeague;
      const data = await fetchValueBets(minEv, leagueParam);
      setValueBets(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBets();
  }, [selectedLeague, minEv]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight flex items-center gap-2.5">
            <Award className="w-7 h-7 text-emerald-400" />
            <span>AI Value Bet Recommendations</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Markets where Portuguese sportsbooks price lines higher than true model probabilities ($EV \ge {minEv}\%$)
          </p>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-2">
          {LEAGUES.map((lg) => (
            <button
              key={lg}
              onClick={() => setSelectedLeague(lg)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                selectedLeague === lg
                  ? "bg-emerald-600 text-white shadow-md shadow-emerald-600/30"
                  : "bg-slate-800/80 text-slate-300 hover:bg-slate-700"
              }`}
            >
              {lg}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <label className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5" />
            <span>Min EV:</span>
          </label>
          <select
            value={minEv}
            onChange={(e) => setMinEv(parseFloat(e.target.value))}
            className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs font-semibold text-white focus:outline-none focus:border-emerald-500"
          >
            <option value={2.0}>+2% EV</option>
            <option value={3.0}>+3% EV (Standard)</option>
            <option value={5.0}>+5% EV (High)</option>
            <option value={10.0}>+10% EV (Ultra Value)</option>
          </select>
        </div>
      </div>

      {/* Value Bets Table */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-sm backdrop-blur">
        <div className="flex items-center justify-between mb-4">
          <span className="text-xs font-semibold text-slate-400">
            Showing <strong className="text-emerald-400">{valueBets.length}</strong> value betting opportunities
          </span>
        </div>

        {loading ? (
          <div className="py-16 text-center text-slate-400 text-sm">
            Scanning Portuguese bookmakers for positive EV...
          </div>
        ) : valueBets.length === 0 ? (
          <div className="py-16 text-center text-slate-500 text-sm">
            No value bets found for this filter criteria. Try lowering the minimum EV or select &quot;All Leagues&quot;.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-800/60 text-slate-400 uppercase font-bold text-[10px] tracking-wider">
                <tr>
                  <th className="py-3 px-4 rounded-l-xl">Match & Competition</th>
                  <th className="py-3 px-4">Market</th>
                  <th className="py-3 px-4">Selection</th>
                  <th className="py-3 px-4">Bookmaker</th>
                  <th className="py-3 px-4">Market Odds</th>
                  <th className="py-3 px-4">Fair Odds (True P)</th>
                  <th className="py-3 px-4">Expected Value</th>
                  <th className="py-3 px-4">Kelly Stake</th>
                  <th className="py-3 px-4 rounded-r-xl text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {valueBets.map((v) => (
                  <tr key={v.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-white text-sm">
                        {v.home_team} vs {v.away_team}
                      </div>
                      <div className="text-[11px] text-slate-400 font-medium">
                        {v.league} &bull; {new Date(v.kickoff).toLocaleDateString("pt-PT", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-slate-300">{v.market_type}</td>
                    <td className="py-3.5 px-4 font-bold text-white">
                      <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                        {v.selection}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="font-semibold text-emerald-400">{v.best_bookmaker}</span>
                    </td>
                    <td className="py-3.5 px-4 font-extrabold text-white text-sm">
                      {v.best_odds.toFixed(2)}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="text-slate-300 font-medium">{v.fair_odds.toFixed(2)}</span>
                      <span className="text-slate-500 ml-1.5">({(v.model_prob * 100).toFixed(1)}%)</span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2.5 py-1 rounded-md text-[11px] font-extrabold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                        +{v.ev_percent.toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-emerald-400">{v.recommended_stake.toFixed(2)} €</div>
                      <div className="text-[10px] text-slate-500">{v.kelly_stake_percent.toFixed(1)}% bankroll</div>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => setSelectedBet(v)}
                        className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition shadow-sm"
                      >
                        Simulate
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedBet && (
        <BetModal
          isOpen={!!selectedBet}
          onClose={() => setSelectedBet(null)}
          onSuccess={loadBets}
          matchId={selectedBet.match_id}
          matchTitle={`${selectedBet.home_team} vs ${selectedBet.away_team}`}
          bookmaker={selectedBet.best_bookmaker}
          selection={selectedBet.selection}
          odds={selectedBet.best_odds}
          recommendedStake={selectedBet.recommended_stake}
          predictionId={selectedBet.id}
        />
      )}
    </div>
  );
}
