-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector" WITH SCHEMA public;

-- Projects table
CREATE TABLE IF NOT EXISTS public.projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    content TEXT,
    create_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    update_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ref_source TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    user_id UUID DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Chats table
CREATE TABLE IF NOT EXISTS public.chats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT,
    content TEXT,
    create_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    update_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ref_source TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    user_id UUID DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Files table
CREATE TABLE IF NOT EXISTS public.files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    path TEXT,
    content TEXT,
    description TEXT,
    file_type TEXT,
    create_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    update_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ref_source TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    user_id UUID DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Media table
CREATE TABLE IF NOT EXISTS public.media (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT,
    description TEXT,
    media_type TEXT,
    url TEXT,
    create_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    update_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ref_source TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    user_id UUID DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE
);

-- MCP logs table
CREATE TABLE IF NOT EXISTS public.mcp_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    context_id TEXT NOT NULL,
    operation TEXT,
    user_id TEXT DEFAULT (auth.uid())::text,
    timestamp BIGINT,
    parameters JSONB DEFAULT '{}'::jsonb,
    result JSONB DEFAULT '{}'::jsonb,
    status TEXT,
    create_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Vector search tables (for semantic search if required)
CREATE TABLE IF NOT EXISTS public.nods_page (
    id BIGSERIAL PRIMARY KEY,
    parent_page_id BIGINT REFERENCES public.nods_page,
    path TEXT NOT NULL UNIQUE,
    checksum TEXT,
    meta JSONB,
    type TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS public.nods_page_section (
    id BIGSERIAL PRIMARY KEY,
    page_id BIGINT NOT NULL REFERENCES public.nods_page ON DELETE CASCADE,
    content TEXT,
    token_count INT,
    embedding VECTOR(1536),
    slug TEXT,
    heading TEXT
);

-- Create vector search function
CREATE OR REPLACE FUNCTION match_page_sections(embedding VECTOR(1536), match_threshold FLOAT, match_count INT, min_content_length INT)
RETURNS TABLE (id BIGINT, page_id BIGINT, slug TEXT, heading TEXT, content TEXT, similarity FLOAT)
LANGUAGE plpgsql
AS $$
#variable_conflict use_variable
BEGIN
    RETURN QUERY
    SELECT
        nods_page_section.id,
        nods_page_section.page_id,
        nods_page_section.slug,
        nods_page_section.heading,
        nods_page_section.content,
        (nods_page_section.embedding <#> embedding) * -1 AS similarity
    FROM nods_page_section
    WHERE length(nods_page_section.content) >= min_content_length
    AND (nods_page_section.embedding <#> embedding) * -1 > match_threshold
    ORDER BY nods_page_section.embedding <#> embedding
    LIMIT match_count;
END;
$$;

-- (No seed data: under the owner-scoped RLS below, rows inserted at setup time
-- have a NULL owner and would be invisible to every authenticated user, so
-- seeding here serves no purpose. Seed real, user-owned data through the app.)

-- ---------------------------------------------------------------------------
-- Row-level security (least privilege)
-- ---------------------------------------------------------------------------
-- With RLS enabled Postgres denies all access unless a policy grants it. The
-- policies below grant the MINIMUM access required:
--   * projects / chats / files / media : an authenticated user may read and
--     write ONLY their own rows (auth.uid() = user_id).
--   * mcp_logs : same ownership model, but user_id is TEXT so it is compared
--     against auth.uid()::text.
--   * nods_page / nods_page_section : shared RAG knowledge base. Authenticated
--     users may READ; writes are reserved for the service role (which bypasses
--     RLS), so no write policy is granted here.
-- The anonymous (anon) role is intentionally granted NO policies and therefore
-- has no access to any of these tables. This replaces the previous
-- "Allow all for now" policies that granted anon full read/write access.

-- Ensure the ownership column exists on pre-existing deployments. This is a
-- no-op on a fresh install where the column is already declared above, but it
-- adds user_id to databases created before ownership was introduced so the
-- policies below can reference it.
--
-- NOTE for existing deployments: rows that predate this column get user_id =
-- NULL and therefore become invisible under the owner-scoped policies. Before
-- relying on RLS, backfill user_id for legacy rows according to your own
-- ownership mapping, e.g.:
--     UPDATE public.projects SET user_id = '<owner-uuid>' WHERE user_id IS NULL;
-- We intentionally do NOT force NOT NULL here: there is no creator column to
-- backfill from generically, and a fresh install seeds no rows.
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS user_id UUID DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.chats    ADD COLUMN IF NOT EXISTS user_id UUID DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.files    ADD COLUMN IF NOT EXISTS user_id UUID DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.media    ADD COLUMN IF NOT EXISTS user_id UUID DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE;

-- mcp_logs.user_id predates this change; ensure it defaults to the caller so
-- authenticated INSERTs satisfy the WITH CHECK (user_id = auth.uid()::text).
ALTER TABLE public.mcp_logs ALTER COLUMN user_id SET DEFAULT (auth.uid())::text;

-- Indexes to keep the ownership predicate fast.
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON public.projects (user_id);
CREATE INDEX IF NOT EXISTS idx_chats_user_id    ON public.chats (user_id);
CREATE INDEX IF NOT EXISTS idx_files_user_id    ON public.files (user_id);
CREATE INDEX IF NOT EXISTS idx_media_user_id    ON public.media (user_id);
CREATE INDEX IF NOT EXISTS idx_mcp_logs_user_id ON public.mcp_logs (user_id);

-- Enable row-level security on every table.
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.files ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.media ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mcp_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nods_page ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nods_page_section ENABLE ROW LEVEL SECURITY;

-- Drop the insecure placeholder policies that granted the anon role full
-- access ("Allow all for now"). Safe to run even if they were never created.
DROP POLICY IF EXISTS "Allow all for now" ON public.projects;
DROP POLICY IF EXISTS "Allow all for now" ON public.chats;
DROP POLICY IF EXISTS "Allow all for now" ON public.files;
DROP POLICY IF EXISTS "Allow all for now" ON public.media;
DROP POLICY IF EXISTS "Allow all for now" ON public.mcp_logs;
DROP POLICY IF EXISTS "Allow all for now" ON public.nods_page;
DROP POLICY IF EXISTS "Allow all for now" ON public.nods_page_section;

-- Owner-scoped policies: an authenticated user may only read/write their own rows.
DROP POLICY IF EXISTS "Users manage their own projects" ON public.projects;
CREATE POLICY "Users manage their own projects" ON public.projects
    FOR ALL TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users manage their own chats" ON public.chats;
CREATE POLICY "Users manage their own chats" ON public.chats
    FOR ALL TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users manage their own files" ON public.files;
CREATE POLICY "Users manage their own files" ON public.files
    FOR ALL TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users manage their own media" ON public.media;
CREATE POLICY "Users manage their own media" ON public.media
    FOR ALL TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- mcp_logs.user_id is TEXT, so compare against the text form of the JWT subject.
DROP POLICY IF EXISTS "Users manage their own mcp_logs" ON public.mcp_logs;
CREATE POLICY "Users manage their own mcp_logs" ON public.mcp_logs
    FOR ALL TO authenticated
    USING (user_id = auth.uid()::text)
    WITH CHECK (user_id = auth.uid()::text);

-- Shared RAG knowledge base: authenticated users may read; writes are reserved
-- for the service role (which bypasses RLS), so no write policy is defined.
DROP POLICY IF EXISTS "Authenticated can read nods_page" ON public.nods_page;
CREATE POLICY "Authenticated can read nods_page" ON public.nods_page
    FOR SELECT TO authenticated
    USING (true);

DROP POLICY IF EXISTS "Authenticated can read nods_page_section" ON public.nods_page_section;
CREATE POLICY "Authenticated can read nods_page_section" ON public.nods_page_section
    FOR SELECT TO authenticated
    USING (true);

-- Restrict the vector-search RPC to authenticated callers (and the service
-- role). It runs SECURITY INVOKER, so it already honours the RLS policies
-- above, but revoking the default PUBLIC grant prevents anon from calling it.
REVOKE ALL ON FUNCTION public.match_page_sections(VECTOR(1536), FLOAT, INT, INT) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.match_page_sections(VECTOR(1536), FLOAT, INT, INT) FROM anon;
GRANT EXECUTE ON FUNCTION public.match_page_sections(VECTOR(1536), FLOAT, INT, INT) TO authenticated, service_role;
