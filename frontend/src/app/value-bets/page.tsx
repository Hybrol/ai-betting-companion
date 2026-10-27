"use client";

import { useEffect, useState } from "react";
import { Award, Filter, Sparkles, TrendingUp, Layers, CheckCircle2, ShieldAlert, Calendar } from "lucide-react";
import BetModal from "@/components/BetModal";
import { fetchValueBets, fetchCuratedMultiple, ValueBetItem, CuratedMultiple } from "@/lib/api";

const LEAGUES = [
  "All Leagues",
  "Premier League",
  "La Liga",
  "Serie A",
  "Bundesliga",
  "Ligue 1",
  "Liga Portugal",
  "Champions League",
  "Europa League",
  "Conference League",
  "Saudi Pro League",
  "UAE Pro League",
  "Qatar Stars League",
];

const MARKET_FORMAT_NAMES: Record<string, string> = {
  "1X2": "1X2 (Resultado Final)",
  "DOUBLE_CHANCE": "Dupla Chance",
  "OVER_UNDER_1_5": "Over/Under 1.5",
  "OVER_UNDER_2_5": "Over/Under 2.5",
  "OVER_UNDER_3_5": "Over/Under 3.5",
  "BTTS": "Ambas Marcam",
};

export default function ValueBetsPage() {
  const [valueBets, setValueBets] = useState<ValueBetItem[]>([]);
  const [curatedMultiple, setCuratedMultiple] = useState<CuratedMultiple | null>(null);
  const [selectedLeague, setSelectedLeague] = useState("All Leagues");
  const [todayOnly, setTodayOnly] = useState(true);
  const [minEv, setMinEv] = useState(3.5);
  const [loading, setLoading] = useState(true);
  const [selectedBet, setSelectedBet] = useState<ValueBetItem | null>(null);

  const loadBets = async (isBackground = false) => {
    try {
      if (!isBackground) setLoading(true);
      const leagueParam = selectedLeague === "All Leagues" ? undefined : selectedLeague;
      const [bets, multiple] = await Promise.all([
        fetchValueBets(minEv, leagueParam, todayOnly),
        fetchCuratedMultiple(todayOnly)
      ]);
      setValueBets(bets);
      setCuratedMultiple(multiple);
    } catch (err) {
      console.error(err);
    } finally {
      if (!isBackground) setLoading(false);
    }
  };

  useEffect(() => {
    loadBets();
    const interval = setInterval(() => {
      loadBets(true);
    }, 20000);
    return () => clearInterval(interval);
  }, [selectedLeague, minEv, todayOnly]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight flex items-center gap-2.5">
            <Award className="w-7 h-7 text-emerald-400" />
            <span>AI Value Bet Recommendations</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Análise quantitativa de valor (+EV) nas casas licenciadas pelo SRIJ em Portugal (Betclic &bull; Betano &bull; Solverde)
          </p>
        </div>
      </div>

      {/* Curated Multiple de Valor do Dia (if available) */}
      {curatedMultiple && (
        <div className="p-5 rounded-2xl bg-gradient-to-r from-purple-950/40 via-indigo-950/30 to-slate-900/60 border border-purple-500/30 shadow-lg backdrop-blur">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
            <div className="flex items-center gap-2.5">
              <span className="p-2 rounded-xl bg-purple-500/20 text-purple-400 border border-purple-500/30">
                <Layers className="w-5 h-5" />
              </span>
              <div>
                <h3 className="text-base font-extrabold text-white flex items-center gap-2">
                  <span>Múltipla de Valor do Dia</span>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    {curatedMultiple.legs_count} Seleções Independentes
                  </span>
                </h3>
                <p className="text-xs text-slate-400">
                  Combinação de alto valor esperado (+{curatedMultiple.combined_ev_percent}% EV) baseada no modelo Dixon-Coles
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4 bg-slate-900/80 px-4 py-2 rounded-xl border border-purple-500/20">
              <div>
                <div className="text-[10px] text-slate-400 uppercase font-semibold">Odd Combinada</div>
                <div className="text-lg font-black text-purple-400">{curatedMultiple.total_odds.toFixed(2)}</div>
              </div>
              <div className="h-8 w-px bg-slate-800" />
              <div>
                <div className="text-[10px] text-slate-400 uppercase font-semibold">Stake Sugerida</div>
                <div className="text-lg font-black text-emerald-400">{curatedMultiple.recommended_stake.toFixed(2)} €</div>
              </div>
              <div className="h-8 w-px bg-slate-800" />
              <div>
                <div className="text-[10px] text-slate-400 uppercase font-semibold">Retorno Possível</div>
                <div className="text-lg font-black text-white">{curatedMultiple.potential_payout.toFixed(2)} €</div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {curatedMultiple.legs.map((leg, idx) => (
              <div key={idx} className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                    <span className="font-semibold text-purple-300">{leg.league}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                      leg.confidence === "ALTA"
                        ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                        : "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                    }`}>
                      Conf. {leg.confidence}
                    </span>
                  </div>
                  <div className="font-bold text-white text-sm">{leg.match}</div>
                  <div className="mt-2 flex items-center justify-between bg-slate-800/60 px-2.5 py-1.5 rounded-lg text-xs">
                    <span className="text-slate-300">{MARKET_FORMAT_NAMES[leg.market] || leg.market}: <strong className="text-white">{leg.selection}</strong></span>
                    <span className="font-black text-emerald-400">{leg.odds.toFixed(2)} ({leg.bookmaker})</span>
                  </div>
                </div>
                <div className="mt-2 text-[11px] text-slate-400 italic line-clamp-2">
                  &ldquo;{leg.reasoning}&rdquo;
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Date Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-850">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setTodayOnly(true)}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
              todayOnly
                ? "bg-emerald-600 text-white shadow-md shadow-emerald-600/30"
                : "bg-slate-800 text-slate-400 hover:text-white"
            }`}
          >
            <Calendar className="w-3.5 h-3.5" />
            <span>Jogos de Hoje</span>
            {todayOnly && (
              <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-emerald-950 text-emerald-300 font-extrabold border border-emerald-500/30">
                Hoje
              </span>
            )}
          </button>
          <button
            onClick={() => setTodayOnly(false)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
              !todayOnly
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                : "bg-slate-800 text-slate-400 hover:text-white"
            }`}
          >
            <span>Todas as Datas</span>
          </button>
        </div>
        <div className="text-xs text-slate-400">
          {todayOnly ? (
            <span className="text-emerald-400 font-semibold">✓ Apenas recomendações de jogos para o dia de hoje</span>
          ) : (
            <span className="text-slate-400">A exibir todas as oportunidades futuras na base de dados</span>
          )}
        </div>
      </div>

      {/* Filters Bar */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-1.5">
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
            <option value={2.5}>+2.5% EV</option>
            <option value={3.5}>+3.5% EV (Elite Standard)</option>
            <option value={5.0}>+5.0% EV (High Edge)</option>
            <option value={8.0}>+8.0% EV (Ultra Value)</option>
          </select>
        </div>
      </div>

      {/* Value Bets Table */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-sm backdrop-blur">
        <div className="flex items-center justify-between mb-4">
          <span className="text-xs font-semibold text-slate-400">
            Apresentando <strong className="text-emerald-400">{valueBets.length}</strong> apostas com edge real de valor
          </span>
        </div>

        {loading ? (
          <div className="py-16 text-center text-slate-400 text-sm">
            A avaliar mercados com o modelo Dixon-Coles e consenso SRIJ...
          </div>
        ) : valueBets.length === 0 ? (
          <div className="py-16 text-center text-slate-500 text-sm">
            Nenhuma oportunidade acima do limite mínimo encontrada no momento. Tente diminuir o EV mínimo ou selecione &quot;All Leagues&quot;.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-800/60 text-slate-400 uppercase font-bold text-[10px] tracking-wider">
                <tr>
                  <th className="py-3 px-4 rounded-l-xl">Jogo & Competição</th>
                  <th className="py-3 px-4">Mercado Exato</th>
                  <th className="py-3 px-4">Seleção</th>
                  <th className="py-3 px-4">Melhor Casa</th>
                  <th className="py-3 px-4">Odd Mercado</th>
                  <th className="py-3 px-4">Odd Justa (P Real)</th>
                  <th className="py-3 px-4">Valor (+EV)</th>
                  <th className="py-3 px-4">Kelly Stake</th>
                  <th className="py-3 px-4 rounded-r-xl text-right">Ação</th>
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
                      {v.reasoning && (
                        <div className="mt-1 text-[11px] text-slate-400 line-clamp-1 italic text-slate-400">
                          &ldquo;{v.reasoning}&rdquo;
                        </div>
                      )}
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-slate-300">
                      {MARKET_FORMAT_NAMES[v.market_type] || v.market_type}
                    </td>
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
                      <div className="flex items-center gap-1.5">
                        <span className="px-2.5 py-1 rounded-md text-[11px] font-extrabold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                          +{v.ev_percent.toFixed(1)}%
                        </span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          v.confidence === "ALTA"
                            ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                            : "bg-blue-500/10 text-blue-300 border border-blue-500/20"
                        }`}>
                          {v.confidence || "MÉDIA"}
                        </span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-emerald-400">{v.recommended_stake.toFixed(2)} €</div>
                      <div className="text-[10px] text-slate-500">{v.kelly_stake_percent.toFixed(1)}% banca</div>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => setSelectedBet(v)}
                        className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition shadow-sm"
                      >
                        Simular
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
