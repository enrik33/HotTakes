import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ReferenceLine,
    ResponsiveContainer,
} from 'recharts';
import { useTimeline } from '../../hooks/useTimeline';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';
import EmptyState from '../ui/EmptyState';

interface ToxicityTrendProps {
    topicId: number;
}

function fmtDate(iso: string) {
    return new Date(iso).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
    });
}

export default function ToxicityTrend({ topicId }: ToxicityTrendProps) {
    const { data, isLoading, error } = useTimeline(topicId);

    if (isLoading) return <LoadingSpinner />;
    if (error) return <ErrorMessage message={(error as Error).message} />;
    if (!data || data.length === 0)
        return (
            <EmptyState
                title="No toxicity data yet"
                description="Toxicity scores are aggregated daily once comments are classified."
            />
        );

    const chartData = data.map((e) => ({
        date: fmtDate(e.date),
        avg_toxicity: e.avg_toxicity,
    }));

    return (
        <div>
            <h2 className="text-base font-semibold mb-5">Average toxicity over time</h2>
            <ResponsiveContainer width="100%" height={260}>
                <LineChart
                    data={chartData}
                    margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
                >
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis
                        dataKey="date"
                        tick={{ fill: '#94a3b8', fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                    />
                    <YAxis
                        domain={[0, 1]}
                        tickFormatter={(v) => v.toFixed(1)}
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
                        formatter={(v: number) => [v.toFixed(3), 'Avg toxicity']}
                    />
                    {/* low / medium / high thresholds */}
                    <ReferenceLine
                        y={0.33}
                        stroke="#4ade80"
                        strokeDasharray="4 3"
                        label={{ value: 'low', fill: '#4ade80', fontSize: 10, position: 'right' }}
                    />
                    <ReferenceLine
                        y={0.66}
                        stroke="#f87171"
                        strokeDasharray="4 3"
                        label={{ value: 'high', fill: '#f87171', fontSize: 10, position: 'right' }}
                    />
                    <Line
                        type="monotone"
                        dataKey="avg_toxicity"
                        stroke="#818cf8"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4 }}
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}
