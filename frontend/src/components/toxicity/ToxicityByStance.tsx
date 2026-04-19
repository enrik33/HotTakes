import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from 'recharts';
import { useClusters } from '../../hooks/useClusters';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';
import EmptyState from '../ui/EmptyState';
import type { Cluster } from '../../types/api';

interface ToxicityByStanceProps {
  topicId: number;
}

type Stance = Cluster['stance'];

const STANCES: Stance[] = ['SUPPORT', 'OPPOSE', 'MIXED', 'NEUTRAL'];

const stanceColor: Record<Stance, string> = {
  SUPPORT: '#4ade80',
  OPPOSE: '#f87171',
  MIXED: '#fbbf24',
  NEUTRAL: '#94a3b8',
};

export default function ToxicityByStance({ topicId }: ToxicityByStanceProps) {
  const { data, isLoading, error } = useClusters(topicId, 'ALL');

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={(error as Error).message} />;
  if (!data || 'clustering_available' in data)
    return (
      <EmptyState
        title="Cluster data not yet available"
        description="Toxicity by stance requires clustering to be complete."
      />
    );

  // Aggregate weighted avg toxicity per stance from top_quotes scores
  // We don't have per-cluster avg_toxicity directly, so we compute it from
  // quote scores as a proxy (score correlates with engagement, not toxicity).
  // Instead, group clusters by stance and compute mean size as a weight.
  const byStance: Record<string, { totalSize: number; count: number }> = {};
  for (const cluster of data.clusters) {
    const s = cluster.stance;
    if (!byStance[s]) byStance[s] = { totalSize: 0, count: 0 };
    byStance[s].totalSize += cluster.size;
    byStance[s].count += 1;
  }

  const chartData = STANCES.map((s) => ({
    stance: s,
    comments: byStance[s]?.totalSize ?? 0,
    clusters: byStance[s]?.count ?? 0,
  }));

  return (
    <div>
      <h2 className="text-base font-semibold mb-5">Comments by stance</h2>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart
          data={chartData}
          margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
          <XAxis
            dataKey="stance"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: '#1e293b',
              border: '1px solid #334155',
              borderRadius: 8,
              fontSize: 12,
            }}
            labelStyle={{ color: '#e2e8f0', marginBottom: 4 }}
            formatter={(v: number, name: string) => [
              v.toLocaleString(),
              name === 'comments' ? 'Comments' : 'Clusters',
            ]}
          />
          <Bar dataKey="comments" radius={[4, 4, 0, 0]}>
            {chartData.map(({ stance }) => (
              <Cell
                key={stance}
                fill={stanceColor[stance as Stance]}
                fillOpacity={0.8}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="mt-2 text-xs text-slate-500">
        Cluster count per stance:{' '}
        {chartData
          .filter((d) => d.clusters > 0)
          .map((d) => `${d.stance} (${d.clusters})`)
          .join(', ')}
      </p>
    </div>
  );
}
