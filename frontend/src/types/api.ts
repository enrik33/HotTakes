// ---------------------------------------------------------------------------
// Topic
// ---------------------------------------------------------------------------

export interface Topic {
  id: number;
  name: string;
  description: string;
  status: string;
  post_count: number;
  comment_count: number;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Clusters
// ---------------------------------------------------------------------------

export interface Quote {
  id: number;
  body: string;
  author_hash: string;
  score: number;
}

export interface Cluster {
  id: number;
  stance: 'SUPPORT' | 'OPPOSE' | 'MIXED' | 'NEUTRAL';
  cluster_label: string;
  size: number;
  keywords: string[];
  representative_comment: Quote | null;
  top_quotes: Quote[];
}

export interface ClustersAvailable {
  topic_id: number;
  clusters: Cluster[];
  total_comments: number;
  clustering_date: string | null;
}

export interface ClustersUnavailable {
  topic_id: number;
  clustering_available: false;
  reason: string;
  classified_comments: number;
  required: number;
}

export type ClustersResponse = ClustersAvailable | ClustersUnavailable;

// ---------------------------------------------------------------------------
// Timeline
// ---------------------------------------------------------------------------

export interface TimelineEntry {
  date: string;
  stance_support_count: number;
  stance_oppose_count: number;
  stance_mixed_count: number;
  stance_neutral_count: number;
  support_pct: number;
  oppose_pct: number;
  mixed_pct: number;
  neutral_pct: number;
  avg_toxicity: number;
  total_comments: number;
}

export interface TimelineResponse {
  topic_id: number;
  timeline: TimelineEntry[];
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: 'ok' | 'degraded';
  version: string;
  uptime_seconds: number;
  timestamp: string;
  db_connection: string;
  scheduler_status: string;
}
