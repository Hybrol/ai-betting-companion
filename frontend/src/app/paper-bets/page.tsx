"use client";

import { useEffect, useState } from "react";
import { History, CheckCircle2, XCircle, Clock, RotateCcw, ShieldAlert, RefreshCw } from "lucide-react";
import { fetchPaperBets, resetBankroll, checkLiveScores, PaperBetItem } from "@/lib/api";

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

                  return (
                    <tr key={b.id} className="hover:bg-slate-800/40 transition">
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
                        <div className="font-bold text-white text-sm flex items-center gap-2">
                          <span>{b.home_team} vs {b.away_team}</span>
                          {b.home_score !== null && b.home_score !== undefined && (
                            <span className="px-2 py-0.5 rounded text-[11px] font-black bg-slate-800 text-emerald-400 border border-slate-700">
                              {b.home_score} - {b.away_score}
                            </span>
                          )}
                          {b.match_status === "IN_PLAY" && (
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
