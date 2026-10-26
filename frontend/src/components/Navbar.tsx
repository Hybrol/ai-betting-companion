"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { TrendingUp, Layers, Award, History, RefreshCw, Settings, Bell, Zap } from "lucide-react";
import { useState, useEffect } from "react";
import { syncMatches, fetchSettings, SystemSettings } from "@/lib/api";
import SettingsModal from "@/components/SettingsModal";

export default function Navbar() {
  const pathname = usePathname();
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sysSettings, setSysSettings] = useState<SystemSettings | null>(null);

  const loadSettings = async () => {
    try {
      const data = await fetchSettings();
      setSysSettings(data);
    } catch (err) {
      // ignore
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleSyncAll = async () => {
    try {
      setSyncing(true);
      setSyncMsg("Syncing Portuguese Sportsbooks...");
      await syncMatches();
      setSyncMsg("Sync Complete!");
      setTimeout(() => setSyncMsg(""), 3000);
      window.location.reload();
    } catch (err: any) {
      setSyncMsg("Sync Failed");
      setTimeout(() => setSyncMsg(""), 3000);
    } finally {
      setSyncing(false);
    }
  };

  const navItems = [
    { name: "Dashboard", href: "/", icon: TrendingUp },
    { name: "+EV Value Bets", href: "/value-bets", icon: Award },
    { name: "Matches & Odds", href: "/matches", icon: Layers },
    { name: "Paper Wagers", href: "/paper-bets", icon: History },
  ];

  return (
    <>
      <header className="sticky top-0 z-50 bg-slate-900/90 backdrop-blur border-b border-slate-800 text-slate-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-700 flex items-center justify-center font-bold text-white shadow-lg shadow-emerald-500/20">
              PT
            </div>
            <div>
              <div className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-emerald-400 to-teal-300 bg-clip-text text-transparent">
                BetCompanion AI
              </div>
              <div className="text-xs text-slate-400 font-medium">Betclic &bull; Betano &bull; Solverde</div>
            </div>
          </div>

          <nav className="flex items-center gap-1 sm:gap-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-semibold transition-all ${
                    active
                      ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                      : "text-slate-300 hover:text-white hover:bg-slate-800/60"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>

          <div className="flex items-center gap-2.5">
            {/* Auto-Bet Badge */}
            <button
              onClick={() => setSettingsOpen(true)}
              className="hidden lg:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-800/80 hover:bg-slate-700 border border-slate-700 transition"
              title="Click to configure Automation & Discord"
            >
              <Zap className={`w-3.5 h-3.5 ${sysSettings?.auto_bet_enabled ? "text-emerald-400" : "text-slate-500"}`} />
              <span className="text-slate-300">Auto-Bet:</span>
              <span className={sysSettings?.auto_bet_enabled ? "text-emerald-400 font-bold" : "text-slate-500"}>
                {sysSettings?.auto_bet_enabled ? "ON" : "OFF"}
              </span>
            </button>

            {/* Discord indicator / Settings button */}
            <button
              onClick={() => setSettingsOpen(true)}
              className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 border border-slate-700 text-slate-300 transition relative"
              title="Settings & Discord Webhook"
            >
              <Settings className="w-4 h-4" />
              {sysSettings?.discord_configured && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-indigo-500 ring-2 ring-slate-900" />
              )}
            </button>

            {/* Sync button */}
            <button
              onClick={handleSyncAll}
              disabled={syncing}
              className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white transition-all shadow-md disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${syncing ? "animate-spin" : ""}`} />
              <span>{syncing ? "Syncing..." : "Sync Odds"}</span>
            </button>
          </div>
        </div>
      </header>

      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={loadSettings}
      />
    </>
  );
}
