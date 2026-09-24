-- Database Migration: Add cluster_id and cluster_label to public.meetings
-- Date: 2026-09-12

ALTER TABLE public.meetings
ADD COLUMN IF NOT EXISTS cluster_id INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS cluster_label TEXT DEFAULT NULL;

-- Indexes for efficient grouping, filtering, and cluster-based queries
CREATE INDEX IF NOT EXISTS idx_meetings_cluster_id ON public.meetings(cluster_id);
CREATE INDEX IF NOT EXISTS idx_meetings_user_cluster ON public.meetings(user_id, cluster_id);
