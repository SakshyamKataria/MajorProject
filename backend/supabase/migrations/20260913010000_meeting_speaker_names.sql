-- Database Migration: Add speaker_names JSONB column to public.meetings
-- Date: 2026-09-13

ALTER TABLE public.meetings
ADD COLUMN IF NOT EXISTS speaker_names JSONB NOT NULL DEFAULT '{}'::jsonb;
