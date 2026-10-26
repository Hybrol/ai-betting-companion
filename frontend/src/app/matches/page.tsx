"use client";

import { useEffect, useState } from "react";
import { Layers, Calendar, Trophy, Sparkles } from "lucide-react";
import ResolveModal from "@/components/ResolveModal";
import BetModal from "@/components/BetModal";
import { fetchMatches, MatchItem } from "@/lib/api";

const LEAGUES = [
  "All Leagues",
  "Liga Portugal",
  "Premier League",
  "La Liga",
  "Serie A",
  "Bundesliga",
  "Champions League",
];

export default function MatchesPage() {
  const [matches, setMatches] = useState<MatchItem[]>([]);
  const [selectedLeague, setSelectedLeague] = useState("All Leagues");
  const [loading, setLoading] = useState(true);

  const [resolvingMatch, setResolvingMatch] = useState<MatchItem | null>(null);
  const [bettingSelection, setBettingSelection] = useState<{
    match: MatchItem;
    bookmaker: string;
    selection: string;
    odds: number;
    recommendedStake?: number;
  } | null>(null);

  const loadMatches = async () => {
    try {
      setLoading(true);
      const leagueParam = selectedLeague === "All Leagues" ? undefined : selectedLeague;
      const data = await fetchMatches(leagueParam);
      setMatches(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMatches();
  }, [selectedLeague]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight flex items-center gap-2.5">
            <Layers className="w-7 h-7 text-emerald-400" />
            <span>Matches & Odds Comparator</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Live 1X2 odds across Portuguese bookmakers: Betclic &bull; Betano &bull; Solverde
          </p>
        </div>
      </div>

      {/* Leagues Selector */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-wrap items-center gap-2">
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

      {/* Matches Grid */}
      {loading ? (
        <div className="py-20 text-center text-slate-400 text-sm">
          Fetching live fixtures & odds from bookmakers...
        </div>
      ) : matches.length === 0 ? (
        <div className="py-20 text-center text-slate-500 text-sm">
          No matches found for {selectedLeague}. Click &quot;Sync Odds&quot; to fetch the latest schedule.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {matches.map((m) => {
            const betclicOdds: Record<string, number> = {};
            const betanoOdds: Record<string, number> = {};
            const solverdeOdds: Record<string, number> = {};

            for (const o of m.odds) {
              if (o.market_type === "1X2") {
                if (o.bookmaker === "Betclic") betclicOdds[o.selection] = o.odds;
                if (o.bookmaker === "Betano") betanoOdds[o.selection] = o.odds;
                if (o.bookmaker === "Solverde") solverdeOdds[o.selection] = o.odds;
              }
            }

            const max1 = Math.max(betclicOdds["1"] || 0, betanoOdds["1"] || 0, solverdeOdds["1"] || 0);
            const maxX = Math.max(betclicOdds["X"] || 0, betanoOdds["X"] || 0, solverdeOdds["X"] || 0);
            const max2 = Math.max(betclicOdds["2"] || 0, betanoOdds["2"] || 0, solverdeOdds["2"] || 0);

            const d = new Date(m.kickoff);
            const dateStr = d.toLocaleDateString("pt-PT", {
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            });

            return (
              <div
                key={m.id}
                className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur flex flex-col justify-between shadow-sm hover:border-slate-700 transition"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[11px] font-bold uppercase text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                      {m.league}
                    </span>
                    <span className="text-[11px] text-slate-400 flex items-center gap-1 font-medium">
                      <Calendar className="w-3 h-3" />
                      {dateStr}
                    </span>
                  </div>

                  {/* Teams */}
                  <div className="mb-4">
                    <div className="text-base font-bold text-white tracking-tight">{m.home_team}</div>
                    <div className="text-xs text-slate-500 font-semibold my-0.5">vs</div>
                    <div className="text-base font-bold text-white tracking-tight">{m.away_team}</div>
                  </div>

                  {/* Odds Table */}
                  <div className="bg-slate-800/50 rounded-xl p-3 border border-slate-700/50 mb-4">
                    <div className="grid grid-cols-4 text-center text-[10px] uppercase font-bold text-slate-400 mb-2">
                      <div className="text-left">Bookie</div>
                      <div>1 (Home)</div>
                      <div>X (Draw)</div>
                      <div>2 (Away)</div>
                    </div>

                    {/* Betclic row */}
                    {Object.keys(betclicOdds).length > 0 && (
                      <div className="grid grid-cols-4 text-center items-center py-1.5 text-xs border-t border-slate-700/40">
                        <span className="text-left font-bold text-red-400">Betclic</span>
                        {["1", "X", "2"].map((sel) => {
                          const o = betclicOdds[sel];
                          const isMax = o && o === (sel === "1" ? max1 : sel === "X" ? maxX : max2);
                          return (
                            <button
                              key={sel}
                              disabled={!o}
                              onClick={() =>
                                setBettingSelection({
                                  match: m,
                                  bookmaker: "Betclic",
                                  selection: sel,
                                  odds: o,
                                })
                              }
                              className={`py-1 px-1.5 rounded font-extrabold transition ${
                                isMax
                                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                                  : "text-slate-200 hover:bg-slate-700"
                              }`}
                            >
                              {o ? o.toFixed(2) : "-"}
                            </button>
                          );
                        })}
                      </div>
                    )}

                    {/* Betano row */}
                    {Object.keys(betanoOdds).length > 0 && (
                      <div className="grid grid-cols-4 text-center items-center py-1.5 text-xs border-t border-slate-700/40">
                        <span className="text-left font-bold text-orange-400">Betano</span>
                        {["1", "X", "2"].map((sel) => {
                          const o = betanoOdds[sel];
                          const isMax = o && o === (sel === "1" ? max1 : sel === "X" ? maxX : max2);
                          return (
                            <button
                              key={sel}
                              disabled={!o}
                              onClick={() =>
                                setBettingSelection({
                                  match: m,
                                  bookmaker: "Betano",
                                  selection: sel,
                                  odds: o,
                                })
                              }
                              className={`py-1 px-1.5 rounded font-extrabold transition ${
                                isMax
                                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                                  : "text-slate-200 hover:bg-slate-700"
                              }`}
                            >
                              {o ? o.toFixed(2) : "-"}
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-slate-800">
                  <span className="text-xs text-slate-400">
                    {m.status === "FINISHED" ? (
                      <strong className="text-emerald-400">
                        Finished ({m.home_score} - {m.away_score})
                      </strong>
                    ) : (
                      "Scheduled"
                    )}
                  </span>
                  <button
                    onClick={() => setResolvingMatch(m)}
                    className="flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
                  >
                    <Trophy className="w-3.5 h-3.5 text-amber-400" />
                    <span>Settle Result</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {resolvingMatch && (
        <ResolveModal
          isOpen={!!resolvingMatch}
          onClose={() => setResolvingMatch(null)}
          onSuccess={loadMatches}
          matchId={resolvingMatch.id}
          homeTeam={resolvingMatch.home_team}
          awayTeam={resolvingMatch.away_team}
        />
      )}

      {bettingSelection && (
        <BetModal
          isOpen={!!bettingSelection}
          onClose={() => setBettingSelection(null)}
          onSuccess={loadMatches}
          matchId={bettingSelection.match.id}
          matchTitle={`${bettingSelection.match.home_team} vs ${bettingSelection.match.away_team}`}
          bookmaker={bettingSelection.bookmaker}
          selection={bettingSelection.selection}
          odds={bettingSelection.odds}
          recommendedStake={20}
        />
      )}
    </div>
  );
}
