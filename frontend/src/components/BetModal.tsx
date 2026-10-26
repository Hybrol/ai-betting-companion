"use client";

import { useState } from "react";
import { X, CheckCircle, AlertCircle } from "lucide-react";
import { placePaperBet } from "@/lib/api";

interface BetModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  matchId: number;
  matchTitle: string;
  bookmaker: string;
  selection: string;
  odds: number;
  recommendedStake?: number;
  predictionId?: number;
}

export default function BetModal({
  isOpen,
  onClose,
  onSuccess,
  matchId,
  matchTitle,
  bookmaker,
  selection,
  odds,
  recommendedStake,
  predictionId,
}: BetModalProps) {
  const [stake, setStake] = useState<number>(recommendedStake || 20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!isOpen) return null;

  const potentialPayout = (stake * odds).toFixed(2);
  const potentialProfit = (stake * odds - stake).toFixed(2);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await placePaperBet({
        match_id: matchId,
        bookmaker,
        market_type: "1X2",
        selection,
        odds,
        stake,
        prediction_id: predictionId,
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to place paper bet.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2 mb-4">
          <span className="px-2.5 py-1 rounded-md text-xs font-bold uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            Paper Wager
          </span>
          <span className="text-xs font-medium text-slate-400">{bookmaker}</span>
        </div>

        <h3 className="text-lg font-bold text-white mb-1">{matchTitle}</h3>
        <div className="text-sm text-slate-400 mb-6 flex items-center justify-between">
          <span>
            Selection: <strong className="text-slate-200">{selection}</strong>
          </span>
          <span>
            Odds: <strong className="text-emerald-400 font-bold">{odds.toFixed(2)}</strong>
          </span>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="text-xs font-semibold text-slate-300">Fictional Stake (€)</label>
              {recommendedStake && (
                <button
                  type="button"
                  onClick={() => setStake(recommendedStake)}
                  className="text-xs text-emerald-400 hover:underline"
                >
                  Apply Kelly ({recommendedStake}€)
                </button>
              )}
            </div>
            <input
              type="number"
              step="0.5"
              min="1"
              max="500"
              value={stake}
              onChange={(e) => setStake(parseFloat(e.target.value) || 0)}
              className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white font-semibold focus:outline-none focus:border-emerald-500 text-sm"
              required
            />
          </div>

          <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/50 space-y-1.5 text-xs text-slate-300">
            <div className="flex justify-between">
              <span>Potential Return:</span>
              <strong className="text-white">{potentialPayout} €</strong>
            </div>
            <div className="flex justify-between">
              <span>Net Profit:</span>
              <strong className="text-emerald-400">+{potentialProfit} €</strong>
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || stake <= 0}
              className="flex-1 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white font-semibold text-xs transition shadow-lg shadow-emerald-600/30 disabled:opacity-50"
            >
              {loading ? "Placing..." : "Confirm Paper Bet"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
