import { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: "up" | "down" | "neutral";
  color?: "emerald" | "rose" | "blue" | "amber";
}

export default function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend = "neutral",
  color = "emerald",
}: StatCardProps) {
  const colorStyles = {
    emerald: "from-emerald-500/10 to-teal-500/5 text-emerald-400 border-emerald-500/20",
    rose: "from-rose-500/10 to-red-500/5 text-rose-400 border-rose-500/20",
    blue: "from-blue-500/10 to-indigo-500/5 text-blue-400 border-blue-500/20",
    amber: "from-amber-500/10 to-yellow-500/5 text-amber-400 border-amber-500/20",
  }[color];

  return (
    <div className={`p-5 rounded-2xl bg-gradient-to-br ${colorStyles} border bg-slate-900/60 backdrop-blur shadow-sm relative overflow-hidden`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{title}</span>
        <div className="p-2 rounded-xl bg-slate-800/80 border border-slate-700/50">
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">{value}</div>
      {subtitle && (
        <div className="mt-2 text-xs font-medium text-slate-400 flex items-center gap-1.5">
          {subtitle}
        </div>
      )}
    </div>
  );
}
