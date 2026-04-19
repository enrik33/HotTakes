import { useState } from 'react';
import { useClusters } from '../../hooks/useClusters';
import ClusterCard from './ClusterCard';
import StanceFilter from './StanceFilter';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';
import EmptyState from '../ui/EmptyState';

type Stance = 'ALL' | 'SUPPORT' | 'OPPOSE' | 'MIXED' | 'NEUTRAL';

interface ClusterGridProps {
  topicId: number;
}

export default function ClusterGrid({ topicId }: ClusterGridProps) {
  const [stance, setStance] = useState<Stance>('ALL');
  const { data, isLoading, error } = useClusters(topicId, stance);

  return (
    <div>
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h2 className="text-base font-semibold">Opinion clusters</h2>
        <StanceFilter value={stance} onChange={setStance} />
      </div>

      {isLoading && <LoadingSpinner />}
      {error && <ErrorMessage message={(error as Error).message} />}

      {data && 'clustering_available' in data && !data.clustering_available && (
        <EmptyState
          title="Clustering not yet available"
          description={`${data.classified_comments} / ${data.required} comments classified. ${data.reason}`}
        />
      )}

      {data && !('clustering_available' in data) && data.clusters.length === 0 && (
        <EmptyState
          title="No clusters for this filter"
          description="Try a different stance filter."
        />
      )}

      {data && !('clustering_available' in data) && data.clusters.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.clusters.map((cluster) => (
            <ClusterCard key={cluster.id} cluster={cluster} />
          ))}
        </div>
      )}
    </div>
  );
}
