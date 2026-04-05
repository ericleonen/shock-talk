'use client';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';

export interface IRFDataPoint {
  period: number;
  [variable: string]: number;
}

interface IRFChartProps {
  data: IRFDataPoint[];
  variables: string[];
}

// Normalize each series so its max absolute value is 1
function normalizeData(data: IRFDataPoint[], variables: string[]): IRFDataPoint[] {
  const maxAbs: Record<string, number> = {};
  for (const v of variables) {
    maxAbs[v] = Math.max(...data.map((d) => Math.abs(d[v] ?? 0)));
  }
  return data.map((d) => {
    const normalized: IRFDataPoint = { period: d.period };
    for (const v of variables) {
      normalized[v] = maxAbs[v] > 0 ? (d[v] ?? 0) / maxAbs[v] : 0;
    }
    return normalized;
  });
}

const LINE_COLORS = [
  '#16a34a', // green-600
  '#3b82f6', // blue-500
  '#8b5cf6', // violet-500
  '#f59e0b', // amber-500
  '#f43f5e', // rose-500
  '#06b6d4', // cyan-500
];

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { name: string; value: number; color: string }[];
  label?: number;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded-md border border-gray-200 bg-white px-3 py-2 shadow-md text-xs">
      <p className="font-semibold text-gray-700 mb-1.5">Period {label}</p>
      {payload.map((entry) => (
        <p key={entry.name} className="flex items-center gap-1.5" style={{ color: entry.color }}>
          <span
            className="inline-block w-2 h-2 rounded-full"
            style={{ background: entry.color }}
          />
          <span className="font-mono">{entry.name}</span>
          <span className="ml-auto pl-3 font-mono text-gray-700">
            {entry.value >= 0 ? '+' : ''}
            {entry.value.toFixed(3)}
          </span>
        </p>
      ))}
    </div>
  );
}

export default function IRFChart({ data, variables }: IRFChartProps) {
  const normalized = normalizeData(data, variables);

  return (
    <div className="rounded-md border border-gray-200 bg-white p-5 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Impulse Response Functions</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Normalized — each series scaled to peak absolute value of 1
          </p>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={normalized} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
          <XAxis
            dataKey="period"
            tick={{ fontSize: 11, fill: '#9ca3af' }}
            tickLine={false}
            axisLine={{ stroke: '#e5e7eb' }}
            label={{
              value: 'Period',
              position: 'insideBottomRight',
              offset: -4,
              fontSize: 11,
              fill: '#9ca3af',
            }}
          />
          <YAxis
            tick={{ fontSize: 11, fill: '#9ca3af' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => v.toFixed(1)}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: '12px', paddingTop: '12px' }}
            iconType="circle"
            iconSize={8}
          />
          <ReferenceLine y={0} stroke="#e5e7eb" strokeWidth={1} />
          {variables.map((v, i) => (
            <Line
              key={v}
              type="monotone"
              dataKey={v}
              stroke={LINE_COLORS[i % LINE_COLORS.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 0 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
