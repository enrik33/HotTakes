import { apiFetch } from './client';
import type { TimelineResponse } from '../types/api';

export function getTimeline(topicId: number): Promise<TimelineResponse> {
  return apiFetch(`/api/timeline?topic_id=${topicId}`);
}
