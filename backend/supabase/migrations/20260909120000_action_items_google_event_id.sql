-- ==============================================================================
-- AI-Powered Meeting & Lecture Intelligence Platform
-- Database Migration: Add google_event_id to public.action_items
-- Tracks Google Calendar Event ID to prevent duplicate calendar event creation
-- ==============================================================================

ALTER TABLE public.action_items 
ADD COLUMN IF NOT EXISTS google_event_id TEXT;

CREATE INDEX IF NOT EXISTS idx_action_items_google_event_id 
ON public.action_items(google_event_id);
