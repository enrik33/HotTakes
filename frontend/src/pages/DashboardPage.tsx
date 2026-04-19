import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getTopics } from '../api/topics';
import AppShell from '../components/layout/AppShell';
import ClusterGrid from '../components/clusters/ClusterGrid';
import TimelineChart from '../components/timeline/TimelineChart';
import ToxicityTrend from '../components/toxicity/ToxicityTrend';
import ToxicityByStance from '../components/toxicity/ToxicityByStance';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import ErrorMessage from '../components/ui/ErrorMessage';

type Tab = 'clusters' | 'timeline' | 'toxicity';

const TABS: { id: Tab; label: string }[] = [
  { id: 'clusters', label: 'Clusters' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'toxicity', label: 'Toxicity' },
];

export default function DashboardPage() {
  const { id } = useParams<{ id: string }>();
  const topicId = Number(id);
  const [tab, setTab] = useState<Tab>('clusters');

  const { data, isLoading, error } = useQuery({
    queryKey: ['topics'],
    queryFn: getTopics,
    select: (d) => d.topics.find((t) => t.id === topicId),
  });

  return (
    <AppShell>
      {/* Breadcrumb */}
      <div className="mb-6 text-sm text-slate-500">
        <Link to="/" className="hover:text-slate-300 transition-colors">
          Topics
        </Link>
        <span className="mx-2">/</span>
        <span className="text-slate-300">
          {data?.name ?? `Topic ${id}`}
        </span>
      </div>

      {/* Header */}
      {isLoading && <LoadingSpinner />}
      {error && <ErrorMessage message={(error as Error).message} />}
      {data && (
        <>
          <div className="mb-6">
            <h1 className="text-2xl font-bold tracking-tight">{data.name}</h1>
            {data.description && (
              <p className="text-slate-400 text-sm mt-1">{data.description}</p>
            )}
            <div className="mt-2 flex gap-4 text-xs text-slate-500">
              <span>{data.post_count.toLocaleString()} posts</span>
              <span>{data.comment_count.toLocaleString()} comments</span>
            </div>
          </div>

          {/* Tab bar */}
          <div className="flex gap-1 border-b border-slate-800 mb-8">
            {TABS.map(({ id: tabId, label }) => (
              <button
                key={tabId}
                onClick={() => setTab(tabId)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px
                  ${tab === tabId
                    ? 'border-slate-300 text-slate-100'
                    : 'border-transparent text-slate-500 hover:text-slate-300'
                  }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Tab panels */}
          {tab === 'clusters' && <ClusterGrid topicId={topicId} />}
          {tab === 'timeline' && <TimelineChart topicId={topicId} />}
          {tab === 'toxicity' && (
            <div className="space-y-12">
              <ToxicityTrend topicId={topicId} />
              <ToxicityByStance topicId={topicId} />
            </div>
          )}
        </>
      )}
    </AppShell>
  );
}
