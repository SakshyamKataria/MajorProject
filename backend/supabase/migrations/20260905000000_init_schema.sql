-- ==============================================================================
-- AI-Powered Meeting & Lecture Intelligence Platform
-- Database Migration: Complete Schema with pgvector
-- Entities: Users (profiles), Meetings, Participants, Transcripts, Summaries,
--           Decisions, ActionItems, MeetingTags, Embeddings, plus RLS & Functions
-- ==============================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ==============================================================================
-- 2. USERS (Profiles linked to Supabase Auth auth.users)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

-- ==============================================================================
-- 3. MEETINGS
-- ==============================================================================
CREATE TYPE meeting_status AS ENUM ('pending', 'uploading', 'processing', 'completed', 'failed');

CREATE TABLE IF NOT EXISTS public.meetings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'Untitled Meeting',
    description TEXT,
    audio_url TEXT,
    duration_seconds INTEGER DEFAULT 0,
    status meeting_status NOT NULL DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

CREATE INDEX IF NOT EXISTS idx_meetings_user_id ON public.meetings(user_id);
CREATE INDEX IF NOT EXISTS idx_meetings_status ON public.meetings(status);
CREATE INDEX IF NOT EXISTS idx_meetings_created_at ON public.meetings(created_at DESC);

-- ==============================================================================
-- 4. PARTICIPANTS
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.participants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID NOT NULL REFERENCES public.meetings(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT,
    speaker_label TEXT, -- e.g., 'SPEAKER_00', 'SPEAKER_01'
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

CREATE INDEX IF NOT EXISTS idx_participants_meeting_id ON public.participants(meeting_id);

-- ==============================================================================
-- 5. TRANSCRIPTS (with ML Sentence Classifier tags & confidence)
-- ==============================================================================
-- Classifier labels: 'action_item', 'decision', 'deadline', 'discussion', 'question'
CREATE TABLE IF NOT EXISTS public.transcripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID NOT NULL REFERENCES public.meetings(id) ON DELETE CASCADE,
    speaker TEXT,
    sentence_order INTEGER NOT NULL,
    start_time NUMERIC(10, 3) NOT NULL DEFAULT 0.0,
    end_time NUMERIC(10, 3) NOT NULL DEFAULT 0.0,
    text TEXT NOT NULL,
    classifier_label TEXT,
    classifier_confidence NUMERIC(5, 4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

CREATE INDEX IF NOT EXISTS idx_transcripts_meeting_order ON public.transcripts(meeting_id, sentence_order ASC);
CREATE INDEX IF NOT EXISTS idx_transcripts_label ON public.transcripts(classifier_label);

-- ==============================================================================
-- 6. SUMMARIES (5-point key takeaways & structured summary)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID NOT NULL REFERENCES public.meetings(id) ON DELETE CASCADE,
    executive_summary TEXT,
    key_points JSONB NOT NULL DEFAULT '[]'::jsonb, -- 5-point takeaways array
    raw_ai_response JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

CREATE INDEX IF NOT EXISTS idx_summaries_meeting_id ON public.summaries(meeting_id);

-- ==============================================================================
-- 7. DECISIONS
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID NOT NULL REFERENCES public.meetings(id) ON DELETE CASCADE,
    decision TEXT NOT NULL,
    context TEXT,
    decided_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

CREATE INDEX IF NOT EXISTS idx_decisions_meeting_id ON public.decisions(meeting_id);

-- ==============================================================================
-- 8. ACTION ITEMS
-- ==============================================================================
CREATE TYPE action_item_priority AS ENUM ('low', 'medium', 'high');
CREATE TYPE action_item_status AS ENUM ('pending', 'in_progress', 'completed');

CREATE TABLE IF NOT EXISTS public.action_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID NOT NULL REFERENCES public.meetings(id) ON DELETE CASCADE,
    task TEXT NOT NULL,
    assignee TEXT,
    deadline TIMESTAMPTZ,
    priority action_item_priority NOT NULL DEFAULT 'medium',
    status action_item_status NOT NULL DEFAULT 'pending',
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    confidence NUMERIC(5, 4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

CREATE INDEX IF NOT EXISTS idx_action_items_meeting_id ON public.action_items(meeting_id);
CREATE INDEX IF NOT EXISTS idx_action_items_status ON public.action_items(status);
CREATE INDEX IF NOT EXISTS idx_action_items_deadline ON public.action_items(deadline);

-- ==============================================================================
-- 9. MEETING TAGS
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.meeting_tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID NOT NULL REFERENCES public.meetings(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW()),
    CONSTRAINT uq_meeting_tag UNIQUE(meeting_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_meeting_tags_meeting_id ON public.meeting_tags(meeting_id);
CREATE INDEX IF NOT EXISTS idx_meeting_tags_tag ON public.meeting_tags(tag);

-- ==============================================================================
-- 10. EMBEDDINGS (pgvector for semantic search)
-- 768 dimensions matches Gemini text-embedding-004
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID NOT NULL REFERENCES public.meetings(id) ON DELETE CASCADE,
    chunk_type TEXT NOT NULL, -- 'summary', 'transcript_chunk', 'decision', 'action_item'
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding vector(768) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

CREATE INDEX IF NOT EXISTS idx_embeddings_meeting_id ON public.embeddings(meeting_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_type ON public.embeddings(chunk_type);

-- HNSW cosine distance index for fast approximate nearest neighbor search
CREATE INDEX IF NOT EXISTS idx_embeddings_vector_hnsw 
ON public.embeddings 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ==============================================================================
-- 11. SEMANTIC SEARCH FUNCTION (pgvector RPC for Supabase Client)
-- ==============================================================================
CREATE OR REPLACE FUNCTION match_meeting_embeddings (
    query_embedding vector(768),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 10,
    filter_user_id uuid DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    meeting_id uuid,
    meeting_title text,
    chunk_type text,
    content text,
    similarity float
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.meeting_id,
        m.title AS meeting_title,
        e.chunk_type,
        e.content,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM public.embeddings e
    JOIN public.meetings m ON m.id = e.meeting_id
    WHERE (filter_user_id IS NULL OR m.user_id = filter_user_id)
      AND (1 - (e.embedding <=> query_embedding)) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$;

-- ==============================================================================
-- 12. AUTOMATIC USER PROFILE CREATION ON SIGNUP TRIGGER
-- ==============================================================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, full_name, avatar_url)
    VALUES (
        NEW.id,
        NEW.email,
        NEW.raw_user_meta_data->>'full_name',
        NEW.raw_user_meta_data->>'avatar_url'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ==============================================================================
-- 13. ROW LEVEL SECURITY (RLS) POLICIES
-- ==============================================================================
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.meetings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transcripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.action_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.meeting_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.embeddings ENABLE ROW LEVEL SECURITY;

-- Profiles: Users can view and update their own profile
CREATE POLICY "Users can view their own profile"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id);

-- Meetings: Users own their meetings
CREATE POLICY "Users can view their own meetings"
    ON public.meetings FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own meetings"
    ON public.meetings FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own meetings"
    ON public.meetings FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own meetings"
    ON public.meetings FOR DELETE
    USING (auth.uid() = user_id);

-- Child Entities: Accessible if the user owns the parent meeting
CREATE POLICY "Users can access participants of their meetings"
    ON public.participants FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.meetings
        WHERE meetings.id = participants.meeting_id AND meetings.user_id = auth.uid()
    ));

CREATE POLICY "Users can access transcripts of their meetings"
    ON public.transcripts FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.meetings
        WHERE meetings.id = transcripts.meeting_id AND meetings.user_id = auth.uid()
    ));

CREATE POLICY "Users can access summaries of their meetings"
    ON public.summaries FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.meetings
        WHERE meetings.id = summaries.meeting_id AND meetings.user_id = auth.uid()
    ));

CREATE POLICY "Users can access decisions of their meetings"
    ON public.decisions FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.meetings
        WHERE meetings.id = decisions.meeting_id AND meetings.user_id = auth.uid()
    ));

CREATE POLICY "Users can access action_items of their meetings"
    ON public.action_items FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.meetings
        WHERE meetings.id = action_items.meeting_id AND meetings.user_id = auth.uid()
    ));

CREATE POLICY "Users can access tags of their meetings"
    ON public.meeting_tags FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.meetings
        WHERE meetings.id = meeting_tags.meeting_id AND meetings.user_id = auth.uid()
    ));

CREATE POLICY "Users can access embeddings of their meetings"
    ON public.embeddings FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.meetings
        WHERE meetings.id = embeddings.meeting_id AND meetings.user_id = auth.uid()
    ));
