"use client";

import { useEffect, useState, Fragment } from "react";
import { History, CheckCircle2, XCircle, Clock, RotateCcw, ShieldAlert, RefreshCw, ChevronDown, ChevronUp, BarChart3, Layers } from "lucide-react";
import { fetchPaperBets, resetBankroll, checkLiveScores, PaperBetItem, MultipleLegItem } from "@/lib/api";

const MARKET_FORMAT_NAMES: Record<string, string> = {
  "1X2": "1X2 (Resultado Final)",
  "DOUBLE_CHANCE": "Dupla Chance",
  "OVER_UNDER_1_5": "Over/Under 1.5",
  "OVER_UNDER_2_5": "Over/Under 2.5",
  "OVER_UNDER_3_5": "Over/Under 3.5",
  "BTTS": "Ambas Marcam",
};

export default function PaperBetsPage() {
  const [bets, setBets] = useState<PaperBetItem[]>([]);
  const [filter, setFilter] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);
  const [checkingLive, setCheckingLive] = useState(false);
  const [expandedBetId, setExpandedBetId] = useState<number | null>(null);

  const toggleExpand = (id: number) => {
    setExpandedBetId((prev) => (prev === id ? null : id));
  };

  const loadBets = async () => {
    try {
      setLoading(true);
      const statusParam = filter === "ALL" ? undefined : filter;
      const data = await fetchPaperBets(statusParam);
      setBets(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBets();
  }, [filter]);

  const handleCheckLive = async () => {
    try {
      setCheckingLive(true);
      await checkLiveScores();
      await loadBets();
    } catch (err) {
      console.error(err);
    } finally {
      setCheckingLive(false);
    }
  };

  const handleReset = async () => {
    if (confirm("Resetar banca virtual para 1.000,00 € e limpar histórico de apostas antigas?")) {
      await resetBankroll(1000);
      loadBets();
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight flex items-center gap-2.5">
            <History className="w-7 h-7 text-emerald-400" />
            <span>Simulated Paper Wagers</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Histórico de apostas virtuais e liquidação automática minuto a minuto via ESPN Scoreboard
          </p>
        </div>
        <div className="flex items-center gap-2 self-start md:self-auto">
          <button
            onClick={handleCheckLive}
            disabled={checkingLive}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-emerald-700 hover:bg-emerald-600 text-white transition shadow-md shadow-emerald-700/20"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${checkingLive ? "animate-spin" : ""}`} />
            <span>{checkingLive ? "A consultar ESPN..." : "Verificar Resultados ESPN"}</span>
          </button>
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 transition border border-slate-700"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Resetar Banca & Histórico</span>
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 p-1 bg-slate-900/60 border border-slate-800 rounded-xl w-fit">
        {["ALL", "PENDING", "GREEN", "RED"].map((status) => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition ${
              filter === status
                ? "bg-emerald-600 text-white shadow-md shadow-emerald-600/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            {status}
          </button>
        ))}
      </div>

      {/* Bets Table */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-sm backdrop-blur">
        {loading ? (
          <div className="py-16 text-center text-slate-400 text-sm">Carregando apostas simuladas...</div>
        ) : bets.length === 0 ? (
          <div className="py-16 text-center text-slate-500 text-sm">
            Nenhuma aposta neste filtro. As oportunidades automáticas serão colocadas no próximo ciclo de 30 minutos!
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-800/60 text-slate-400 uppercase font-bold text-[10px] tracking-wider">
                <tr>
                  <th className="py-3 px-4 rounded-l-xl">Estado</th>
                  <th className="py-3 px-4">Jogo & Liga</th>
                  <th className="py-3 px-4">Mercado</th>
                  <th className="py-3 px-4">Seleção</th>
                  <th className="py-3 px-4">Casa (SRIJ)</th>
                  <th className="py-3 px-4">Odd</th>
                  <th className="py-3 px-4">Stake</th>
                  <th className="py-3 px-4">Retorno Potencial</th>
                  <th className="py-3 px-4 rounded-r-xl text-right">Resultado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {bets.map((b) => {
                  const isGreen = b.status === "GREEN";
                  const isRed = b.status === "RED";
                  const isPending = b.status === "PENDING";
                  const isExpanded = expandedBetId === b.id;

                  return (
                    <Fragment key={b.id}>
                      <tr className={`hover:bg-slate-800/40 transition ${b.is_multiple ? "bg-purple-950/10 border-l-2 border-purple-500" : ""}`}>
                        <td className="py-3.5 px-4">
                          {isGreen && (
                            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-extrabold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 w-fit">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              <span>GREEN</span>
                            </span>
                          )}
                          {isRed && (
                            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-extrabold bg-rose-500/20 text-rose-400 border border-rose-500/30 w-fit">
                              <XCircle className="w-3.5 h-3.5" />
                              <span>RED</span>
                            </span>
                          )}
                          {isPending && (
                            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 w-fit">
                              <Clock className="w-3.5 h-3.5" />
                              <span>PENDING</span>
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4">
                          {b.is_multiple ? (
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-black bg-purple-500/20 text-purple-300 border border-purple-500/30">
                                  <Layers className="w-3 h-3 text-purple-400" />
                                  <span>MÚLTIPLA DE VALOR ({b.multiple_legs?.length || 3} JOGOS)</span>
                                </span>
                              </div>
                              <div className="text-[11px] text-slate-400 font-medium mt-1">
                                SRIJ &bull; {new Date(b.placed_at).toLocaleDateString("pt-PT", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                              </div>
                              <button
                                onClick={() => toggleExpand(b.id)}
                                className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold bg-slate-800 hover:bg-slate-700 text-purple-300 border border-purple-500/30 transition shadow-sm"
                              >
                                <BarChart3 className="w-3.5 h-3.5 text-purple-400" />
                                <span>{isExpanded ? "Ocultar Estatísticas" : "Ver Análise Estatística das Equipas"}</span>
                                {isExpanded ? <ChevronUp className="w-3.5 h-3.5 ml-1" /> : <ChevronDown className="w-3.5 h-3.5 ml-1" />}
                              </button>
                            </div>
                          ) : (
                            <div>
                              <div className="font-bold text-white text-sm flex items-center gap-2">
                                <span>{b.home_team} vs {b.away_team}</span>
                                {b.home_score !== null && b.home_score !== undefined && (
                                  <span className="px-2 py-0.5 rounded text-[11px] font-black bg-slate-800 text-emerald-400 border border-slate-700">
                                    {b.home_score} - {b.away_score}
                                  </span>
                                )}
                                {(b.match_status === "LIVE" || b.match_status === "IN_PLAY") && (
                                  <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse">
                                    AO VIVO
                                  </span>
                                )}
                              </div>
                              <div className="text-[11px] text-slate-400 font-medium">
                                {b.league} &bull; {new Date(b.placed_at).toLocaleDateString("pt-PT", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                              </div>
                              {b.reasoning && (
                                <div className="mt-1 text-[11px] text-slate-400 line-clamp-1 italic text-slate-400">
                                  &ldquo;{b.reasoning}&rdquo;
                                </div>
                              )}
                            </div>
                          )}
                        </td>
                        <td className="py-3.5 px-4 font-semibold text-slate-300">
                          {MARKET_FORMAT_NAMES[b.market_type] || b.market_type}
                        </td>
                        <td className="py-3.5 px-4 font-bold text-white">
                          <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                            {b.selection}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 font-semibold text-emerald-400">{b.bookmaker}</td>
                        <td className="py-3.5 px-4 font-extrabold text-white text-sm">{b.odds.toFixed(2)}</td>
                        <td className="py-3.5 px-4 font-bold text-slate-200">{b.stake.toFixed(2)} €</td>
                        <td className="py-3.5 px-4 text-slate-300 font-medium">
                          {b.potential_payout.toFixed(2)} €
                        </td>
                        <td className="py-3.5 px-4 text-right font-extrabold text-sm">
                          {isGreen && <span className="text-emerald-400">+{b.profit_loss.toFixed(2)} €</span>}
                          {isRed && <span className="text-rose-400">{b.profit_loss.toFixed(2)} €</span>}
                          {isPending && <span className="text-slate-500">Pendente</span>}
                        </td>
                      </tr>

                      {/* Expanded Multiple Legs and Team Statistics Drawer */}
                      {b.is_multiple && isExpanded && b.multiple_legs && (
                        <tr className="bg-slate-950/80 border-b border-purple-900/30">
                          <td colSpan={9} className="p-4 sm:p-6">
                            <div className="space-y-4">
                              <div className="flex items-center justify-between">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-purple-300 flex items-center gap-2">
                                  <BarChart3 className="w-4 h-4 text-purple-400" />
                                  <span>Dossiê Estatístico Detalhado por Jogo e Equipa</span>
                                </h4>
                                <span className="text-[11px] text-slate-400">Dados oficiais via ESPN Scoreboard & Dixon-Coles</span>
                              </div>

                              <div className="grid grid-cols-1 gap-4">
                                {b.multiple_legs.map((leg, legIdx) => {
                                  const stats = leg.stats_analysis;
                                  const legGreen = leg.status === "GREEN";
                                  const legRed = leg.status === "RED";

                                  return (
                                    <div key={legIdx} className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-3">
                                      {/* Leg Header */}
                                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800">
                                        <div className="flex items-center gap-2">
                                          <span className="w-6 h-6 rounded-full bg-purple-500/20 text-purple-300 flex items-center justify-center text-xs font-bold">
                                            {legIdx + 1}
                                          </span>
                                          <span className="font-extrabold text-white text-sm">{leg.match}</span>
                                          <span className="text-xs text-slate-400">({leg.league})</span>
                                          {leg.home_score !== null && leg.home_score !== undefined && (
                                            <span className="px-2 py-0.5 rounded text-[11px] font-black bg-slate-800 text-emerald-400 border border-slate-700">
                                              {leg.home_score} - {leg.away_score}
                                            </span>
                                          )}
                                          {(leg.match_status === "LIVE" || leg.match_status === "IN_PLAY") && (
                                            <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse">
                                              AO VIVO
                                            </span>
                                          )}
                                        </div>
                                        <div className="flex items-center gap-2">
                                          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-slate-800 text-slate-200 border border-slate-700">
                                            {MARKET_FORMAT_NAMES[leg.market] || leg.market}: <strong className="text-white">{leg.selection}</strong>
                                          </span>
                                          <span className="px-2 py-0.5 rounded text-[11px] font-black bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                            @{leg.odds.toFixed(2)} ({leg.bookmaker})
                                          </span>
                                          {legGreen && (
                                            <span className="px-2 py-0.5 rounded text-[10px] font-extrabold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                                              ACERTOU
                                            </span>
                                          )}
                                          {legRed && (
                                            <span className="px-2 py-0.5 rounded text-[10px] font-extrabold bg-rose-500/20 text-rose-400 border border-rose-500/30">
                                              FALHOU
                                            </span>
                                          )}
                                        </div>
                                      </div>

                                      {/* Teams Detailed Stats Cards */}
                                      {stats ? (
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                                          {/* Home Team Stats */}
                                          <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-750 space-y-1.5">
                                            <div className="flex items-center justify-between font-bold text-white">
                                              <span className="text-emerald-400">🏠 {stats.home.name} (Casa)</span>
                                              <span className="text-[11px] text-slate-300">Posição: {stats.home.rank} ({stats.home.points} pts)</span>
                                            </div>
                                            <div className="text-[11px] text-slate-400 flex items-center justify-between">
                                              <span>Registo: <strong className="text-slate-200">{stats.home.record}</strong></span>
                                              <span>DG: <strong className="text-slate-200">{stats.home.goal_diff}</strong></span>
                                            </div>
                                            <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
                                              <span>Forma (Últimos Jogos):</span>
                                              <div className="flex gap-1">
                                                {stats.home.last_matches.map((m, mIdx) => (
                                                  <span
                                                    key={mIdx}
                                                    title={`${m.result} vs ${m.opponent} (${m.score})`}
                                                    className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                                      m.result === "W" ? "bg-emerald-500/20 text-emerald-300" :
                                                      m.result === "L" ? "bg-rose-500/20 text-rose-300" :
                                                      "bg-amber-500/20 text-amber-300"
                                                    }`}
                                                  >
                                                    {m.result}
                                                  </span>
                                                ))}
                                              </div>
                                            </div>
                                            <div className="text-[11px] text-slate-400">
                                              xG Esperado Casa: <strong className="text-slate-200">{stats.dixon_coles.xg_home.toFixed(2)}</strong>
                                            </div>
                                          </div>

                                          {/* Away Team Stats */}
                                          <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-750 space-y-1.5">
                                            <div className="flex items-center justify-between font-bold text-white">
                                              <span className="text-cyan-400">✈️ {stats.away.name} (Fora)</span>
                                              <span className="text-[11px] text-slate-300">Posição: {stats.away.rank} ({stats.away.points} pts)</span>
                                            </div>
                                            <div className="text-[11px] text-slate-400 flex items-center justify-between">
                                              <span>Registo: <strong className="text-slate-200">{stats.away.record}</strong></span>
                                              <span>DG: <strong className="text-slate-200">{stats.away.goal_diff}</strong></span>
                                            </div>
                                            <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
                                              <span>Forma (Últimos Jogos):</span>
                                              <div className="flex gap-1">
                                                {stats.away.last_matches.map((m, mIdx) => (
                                                  <span
                                                    key={mIdx}
                                                    title={`${m.result} vs ${m.opponent} (${m.score})`}
                                                    className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                                      m.result === "W" ? "bg-emerald-500/20 text-emerald-300" :
                                                      m.result === "L" ? "bg-rose-500/20 text-rose-300" :
                                                      "bg-amber-500/20 text-amber-300"
                                                    }`}
                                                  >
                                                    {m.result}
                                                  </span>
                                                ))}
                                              </div>
                                            </div>
                                            <div className="text-[11px] text-slate-400">
                                              xG Esperado Fora: <strong className="text-slate-200">{stats.dixon_coles.xg_away.toFixed(2)}</strong>
                                            </div>
                                          </div>
                                        </div>
                                      ) : null}

                                      {/* Tipster Rationale */}
                                      {leg.reasoning && (
                                        <div className="text-[11px] text-slate-300 italic bg-slate-800/20 p-2.5 rounded-lg border border-slate-800">
                                          &ldquo;{leg.reasoning}&rdquo;
                                        </div>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
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
    </div>
  );
}
