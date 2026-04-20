import type { Cluster } from '../../types/api';
import Card from '../ui/Card';
import QuoteCard from './QuoteCard';

type Stance = Cluster['stance'];

const accentColor: Record<Stance, string> = {
    SUPPORT: 'border-l-green-400',
    OPPOSE: 'border-l-red-400',
    MIXED: 'border-l-amber-400',
    NEUTRAL: 'border-l-slate-400',
};

const stanceBadge: Record<Stance, string> = {
    SUPPORT: 'text-green-400',
    OPPOSE: 'text-red-400',
    MIXED: 'text-amber-400',
    NEUTRAL: 'text-slate-400',
};

interface ClusterCardProps {
    cluster: Cluster;
}

export default function ClusterCard({ cluster }: ClusterCardProps) {
    return (
        <Card className={`border-l-4 ${accentColor[cluster.stance]}`}>
            <div className="flex items-start justify-between gap-2 mb-3">
                <h3 className="font-semibold text-slate-100 text-sm leading-snug">
                    {cluster.cluster_label}
                </h3>
                <span className={`text-xs font-medium shrink-0 ${stanceBadge[cluster.stance]}`}>
                    {cluster.stance}
                </span>
            </div>

            {cluster.keywords.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-4">
                    {cluster.keywords.map((kw) => (
                        <span
                            key={kw}
                            className="px-2 py-0.5 rounded-full bg-slate-700/60 text-xs text-slate-400"
                        >
                            {kw}
                        </span>
                    ))}
                </div>
            )}

            {cluster.representative_comment && (
                <QuoteCard quote={cluster.representative_comment} />
            )}

            <p className="mt-3 text-xs text-slate-500">
                {cluster.size.toLocaleString()} comment{cluster.size !== 1 ? 's' : ''}
            </p>
        </Card>
    );
}
