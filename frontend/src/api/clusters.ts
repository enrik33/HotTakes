import { apiFetch } from './client';
import type { ClustersResponse } from '../types/api';

export function getClusters(
    topicId: number,
    stance?: string,
): Promise<ClustersResponse> {
    const params = new URLSearchParams({ topic_id: String(topicId) });
    if (stance && stance !== 'ALL') params.set('stance', stance);
    return apiFetch(`/api/clusters?${params}`);
}
