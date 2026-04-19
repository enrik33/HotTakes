import { apiFetch } from './client';
import type { Topic } from '../types/api';

export function getTopics(): Promise<{ topics: Topic[] }> {
  return apiFetch('/api/topics');
}

export function createTopic(data: {
  name: string;
  description?: string;
}): Promise<Topic> {
  return apiFetch('/api/topics', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}
