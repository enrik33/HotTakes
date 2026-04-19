import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { useTimeline } from '../../hooks/useTimeline';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';
import EmptyState from '../ui/EmptyState';

interface TimelineChartProps {
  topicId: number;
}

const AREAS = [
  { key: 'support_pct', label: 'Support', color: '#4ade80' },
  { key: 'oppose_pct', label: 'Oppose', color: '#f87171' },
  { key: 'mixed_pct', label: 'Mixed', color: '#fbbf24' },
  { key: 'neutral_pct', label: 'Neutral', color: '#94a3b8' },
] as const;

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });
}

function fmtPct(v: number) {
  return `${(v * 100).toFixed(1)}%`;
}

export default function TimelineChart({ topicId }: TimelineChartProps) {
  const { data, isLoading, error } = useTimeline(topicId);

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={(error as Error).message} />;
  if (!data || data.length === 0)
    return (
      <EmptyState
        title="No timeline data yet"
        description="Daily stats are computed once enough comments have been classified."
      />
    );

  const chartData = data.map((e) => ({
    date: fmtDate(e.date),
    support_pct: e.support_pct,
    oppose_pct: e.oppose_pct,
    mixed_pct: e.mixed_pct,
    neutral_pct: e.neutral_pct,
    total: e.total_comments,
  }));

  return (
    <div>
      <h2 className="text-base font-semibold mb-5">Stance over time</h2>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart
          data={chartData}
          margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
        >
          <defs>
            {AREAS.map(({ key, color }) => (
              <linearGradient
                key={key}
                id={`grad-${key}`}
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop offset="5%" stopColor={color} stopOpacity={0.35} />
                <stop offset="95%" stopColor={color} stopOpacity={0.05} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="date"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            domain={[0, 1]}
          />
          <Tooltip
            contentStyle={{
              background: '#1e293b',
              border: '1px solid #334155',
              borderRadius: 8,
              fontSize: 12,
            }}
            labelStyle={{ color: '#e2e8f0', marginBottom: 4 }}
            formatter={(value: number, name: string) => [
              fmtPct(value),
              name,
            ]}
          />
          <Legend
            wrapperStyle={{ fontSize: 12, color: '#94a3b8' }}
            iconType="circle"
            iconSize={8}
          />
          {AREAS.map(({ key, label, color }) => (
            <Area
              key={key}
              type="monotone"
              dataKey={key}
              name={label}
              stackId="1"
              stroke={color}
              fill={`url(#grad-${key})`}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
