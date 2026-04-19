import { useQuery } from '@tanstack/react-query';
import { getClusters } from '../api/clusters';

export function useClusters(topicId: number, stance: string) {
  return useQuery({
    queryKey: ['clusters', topicId, stance],
    queryFn: () => getClusters(topicId, stance),
    enabled: topicId > 0,
    refetchInterval: 5 * 60 * 1000,
  });
}
