import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTopics, createTopic } from '../api/topics';

export function useTopics() {
  return useQuery({
    queryKey: ['topics'],
    queryFn: getTopics,
    select: (data) => data.topics,
    refetchInterval: 5 * 60 * 1000,
  });
}

export function useCreateTopic() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createTopic,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['topics'] }),
  });
}
