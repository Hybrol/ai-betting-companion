"use client";

import { useState } from "react";
import { X, Trophy, AlertCircle } from "lucide-react";
import { resolveMatch } from "@/lib/api";

interface ResolveModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  matchId: number;
  homeTeam: string;
  awayTeam: string;
}

export default function ResolveModal({
  isOpen,
  onClose,
  onSuccess,
  matchId,
  homeTeam,
  awayTeam,
}: ResolveModalProps) {
  const [homeScore, setHomeScore] = useState<number>(1);
  const [awayScore, setAwayScore] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await resolveMatch(matchId, homeScore, awayScore);
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to resolve match");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-sm p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2 mb-4 text-emerald-400">
          <Trophy className="w-5 h-5" />
          <h3 className="text-base font-bold text-white">Settle Match Result</h3>
        </div>

        <p className="text-xs text-slate-400 mb-6">
          Enter final score to evaluate open wagers as <strong className="text-emerald-400">GREEN (Won)</strong> or <strong className="text-rose-400">RED (Lost)</strong>.
        </p>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4 text-center">
            <div className="p-3 bg-slate-800/60 rounded-xl border border-slate-700/60">
              <span className="block text-xs font-semibold text-slate-300 truncate mb-2">{homeTeam}</span>
              <input
                type="number"
                min="0"
                max="20"
                value={homeScore}
                onChange={(e) => setHomeScore(parseInt(e.target.value) || 0)}
                className="w-16 mx-auto text-center py-2 text-xl font-extrabold rounded-lg bg-slate-900 border border-slate-600 text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div className="p-3 bg-slate-800/60 rounded-xl border border-slate-700/60">
              <span className="block text-xs font-semibold text-slate-300 truncate mb-2">{awayTeam}</span>
              <input
                type="number"
                min="0"
                max="20"
                value={awayScore}
                onChange={(e) => setAwayScore(parseInt(e.target.value) || 0)}
                className="w-16 mx-auto text-center py-2 text-xl font-extrabold rounded-lg bg-slate-900 border border-slate-600 text-white focus:outline-none focus:border-emerald-500"
              />
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
              disabled={loading}
              className="flex-1 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white font-semibold text-xs transition shadow-lg shadow-emerald-600/30"
            >
              {loading ? "Settling..." : "Settle Bets"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
