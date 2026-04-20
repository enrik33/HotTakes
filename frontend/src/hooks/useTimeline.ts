import { useQuery } from '@tanstack/react-query';
import { getTimeline } from '../api/timeline';

export function useTimeline(topicId: number) {
    return useQuery({
        queryKey: ['timeline', topicId],
        queryFn: () => getTimeline(topicId),
        enabled: topicId > 0,
        select: (d) => d.timeline,
        refetchInterval: 5 * 60 * 1000,
    });
}
