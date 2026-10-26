"use client";

import { useState, useEffect } from "react";
import { X, Bell, Zap, Clock, Send, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";
import { fetchSettings, updateSettings, testDiscordWebhook, triggerCronCycleNow, SystemSettings } from "@/lib/api";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

export default function SettingsModal({ isOpen, onClose, onSaved }: SettingsModalProps) {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [autoBet, setAutoBet] = useState(true);
  const [loading, setLoading] = useState(false);
  const [testingDiscord, setTestingDiscord] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [runningCycle, setRunningCycle] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadSettings();
    }
  }, [isOpen]);

  const loadSettings = async () => {
    try {
      const data = await fetchSettings();
      setSettings(data);
      setAutoBet(data.auto_bet_enabled);
      setWebhookUrl(data.discord_webhook_preview ? "" : "");
    } catch (err) {
      console.error(err);
    }
  };

  if (!isOpen) return null;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setStatusMsg(null);
    try {
      await updateSettings({
        auto_bet_enabled: autoBet,
        discord_webhook_url: webhookUrl.trim() ? webhookUrl.trim() : undefined,
      });
      setStatusMsg({ type: "success", text: "Settings saved successfully!" });
      if (onSaved) onSaved();
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Failed to save settings" });
    } finally {
      setLoading(false);
    }
  };

  const handleTestDiscord = async () => {
    setTestingDiscord(true);
    setStatusMsg(null);
    try {
      const res = await testDiscordWebhook(webhookUrl.trim() || undefined);
      setStatusMsg({ type: "success", text: "Test alert dispatched to Discord channel!" });
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Discord test failed." });
    } finally {
      setTestingDiscord(false);
    }
  };

  const handleRunNow = async () => {
    setRunningCycle(true);
    setStatusMsg(null);
    try {
      await triggerCronCycleNow();
      setStatusMsg({ type: "success", text: "30-min betting scan initiated!" });
      setTimeout(() => {
        if (onSaved) onSaved();
      }, 3000);
    } catch (err: any) {
      setStatusMsg({ type: "error", text: "Failed to trigger scan" });
    } finally {
      setRunningCycle(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-lg p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-slate-400 hover:text-white p-1 rounded-xl hover:bg-slate-800 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2.5 mb-1">
          <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Automation & Discord Alerts</h3>
            <p className="text-xs text-slate-400">Configure auto-gambling and 30-minute notifications</p>
          </div>
        </div>

        {statusMsg && (
          <div
            className={`my-4 p-3 rounded-xl border text-xs flex items-center gap-2 ${
              statusMsg.type === "success"
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                : "bg-rose-500/10 border-rose-500/30 text-rose-400"
            }`}
          >
            {statusMsg.type === "success" ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
            <span>{statusMsg.text}</span>
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-5 mt-5">
          {/* Auto-Betting Switch */}
          <div className="p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60 flex items-center justify-between">
            <div className="pr-4">
              <div className="text-sm font-bold text-white flex items-center gap-2">
                <span>Automatic Paper Gambling</span>
                {autoBet ? (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-extrabold uppercase border border-emerald-500/30">
                    Active
                  </span>
                ) : (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-700 text-slate-400 font-extrabold uppercase">
                    Disabled
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Automatically places simulated bets using Kelly-sized stakes as soon as positive EV opportunities surface.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setAutoBet(!autoBet)}
              className={`w-12 h-6 flex items-center rounded-full p-1 transition duration-300 ${
                autoBet ? "bg-emerald-600 justify-end" : "bg-slate-700 justify-start"
              }`}
            >
              <div className="bg-white w-4 h-4 rounded-full shadow-md" />
            </button>
          </div>

          {/* 30-Minute Cron Info */}
          <div className="p-4 rounded-2xl bg-slate-800/40 border border-slate-700/50 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 text-emerald-400" />
              <div>
                <div className="text-xs font-bold text-white">Cron Inspection Frequency</div>
                <div className="text-[11px] text-slate-400">Scans Betclic &bull; Betano &bull; Solverde every 30 minutes</div>
              </div>
            </div>
            <button
              type="button"
              onClick={handleRunNow}
              disabled={runningCycle}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${runningCycle ? "animate-spin" : ""}`} />
              <span>{runningCycle ? "Scanning..." : "Run Now"}</span>
            </button>
          </div>

          {/* Discord Webhook Input */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Bell className="w-3.5 h-3.5 text-indigo-400" />
                <span>Discord Webhook URL</span>
              </span>
              {settings?.discord_configured && (
                <span className="text-[10px] text-emerald-400 font-semibold flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Connected
                </span>
              )}
            </label>
            <input
              type="url"
              placeholder="https://discord.com/api/webhooks/..."
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white font-medium focus:outline-none focus:border-emerald-500 text-xs"
            />
            <p className="text-[11px] text-slate-400">
              When a good bet is discovered, a rich alert will be sent with the odds of each casino for that match.
            </p>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              type="button"
              onClick={handleTestDiscord}
              disabled={testingDiscord || (!webhookUrl && !settings?.discord_configured)}
              className="flex-1 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs transition border border-slate-700 flex items-center justify-center gap-1.5 disabled:opacity-40"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{testingDiscord ? "Sending..." : "Test Webhook"}</span>
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition shadow-lg shadow-emerald-600/30 disabled:opacity-50"
            >
              {loading ? "Saving..." : "Save Settings"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
