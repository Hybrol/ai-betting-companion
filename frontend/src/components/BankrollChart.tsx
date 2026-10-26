"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

interface HistoryPoint {
  timestamp: string;
  balance: number;
  delta: number;
  description: string;
}

interface BankrollChartProps {
  history: HistoryPoint[];
  initialBalance: number;
}

export default function BankrollChart({ history, initialBalance }: BankrollChartProps) {
  if (!history || history.length === 0) {
    return (
      <div className="h-72 flex items-center justify-center text-slate-500 text-sm">
        No bankroll activity recorded yet.
      </div>
    );
  }

  const chartData = history.map((pt, i) => {
    const d = new Date(pt.timestamp);
    const timeLabel = isNaN(d.getTime())
      ? `Step ${i + 1}`
      : d.toLocaleDateString("pt-PT", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
    return {
      index: i + 1,
      time: timeLabel,
      balance: pt.balance,
      delta: pt.delta,
      desc: pt.description,
    };
  });

  const minVal = Math.floor(Math.min(...chartData.map((d) => d.balance)) * 0.95);
  const maxVal = Math.ceil(Math.max(...chartData.map((d) => d.balance)) * 1.05);

  return (
    <div className="w-full h-80 pt-4">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="balanceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="time"
            stroke="#64748b"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: "#334155" }}
          />
          <YAxis
            domain={[minVal, maxVal]}
            stroke="#64748b"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: "#334155" }}
            tickFormatter={(val) => `${val}€`}
          />
          <ReferenceLine
            y={initialBalance}
            stroke="#94a3b8"
            strokeDasharray="4 4"
            label={{ value: "Initial 1,000€", fill: "#94a3b8", fontSize: 11, position: "insideTopLeft" }}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload;
                return (
                  <div className="p-3 bg-slate-800/95 border border-slate-700 rounded-xl shadow-xl text-xs backdrop-blur">
                    <div className="text-slate-400 font-semibold mb-1">{data.time}</div>
                    <div className="text-base font-extrabold text-emerald-400 mb-1">
                      {data.balance.toFixed(2)} €
                    </div>
                    <div className="text-slate-300 max-w-xs">{data.desc}</div>
                  </div>
                );
              }
              return null;
            }}
          />
          <Area
            type="monotone"
            dataKey="balance"
            stroke="#10b981"
            strokeWidth={3}
            fillOpacity={1}
            fill="url(#balanceGrad)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
