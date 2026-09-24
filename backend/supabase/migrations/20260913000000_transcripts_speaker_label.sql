-- Database Migration: Add speaker_label column to public.transcripts
-- Date: 2026-09-13

ALTER TABLE public.transcripts
ADD COLUMN IF NOT EXISTS speaker_label TEXT DEFAULT NULL;

-- Indexes for efficient queries and filtering by speaker
CREATE INDEX IF NOT EXISTS idx_transcripts_speaker_label ON public.transcripts(speaker_label);
CREATE INDEX IF NOT EXISTS idx_transcripts_meeting_speaker ON public.transcripts(meeting_id, speaker_label);
