-- ==============================================================================
-- AI-Powered Meeting & Lecture Intelligence Platform
-- Database Migration: Google Calendar Integration - User OAuth Tokens Table
-- Stores OAuth tokens per user server-side with RLS and cascade deletion
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.calendar_tokens (
    user_id UUID PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expiry TIMESTAMPTZ NOT NULL,
    connected_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW()),
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

-- Index for fast lookup by user_id
CREATE INDEX IF NOT EXISTS idx_calendar_tokens_user_id ON public.calendar_tokens(user_id);

-- Enable Row Level Security (RLS)
ALTER TABLE public.calendar_tokens ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Users can only access, modify, or delete their own calendar tokens
CREATE POLICY "Users can view their own calendar tokens"
    ON public.calendar_tokens FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own calendar tokens"
    ON public.calendar_tokens FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own calendar tokens"
    ON public.calendar_tokens FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own calendar tokens"
    ON public.calendar_tokens FOR DELETE
    USING (auth.uid() = user_id);
