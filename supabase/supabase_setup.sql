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
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Chats table
CREATE TABLE IF NOT EXISTS public.chats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT,
    content TEXT,
    create_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    update_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ref_source TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
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
    metadata JSONB DEFAULT '{}'::jsonb
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
    metadata JSONB DEFAULT '{}'::jsonb
);

-- MCP logs table
CREATE TABLE IF NOT EXISTS public.mcp_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    context_id TEXT NOT NULL,
    operation TEXT,
    user_id TEXT,
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

-- Create sample data for testing
INSERT INTO public.projects (name, description, content, ref_source)
VALUES
('Abacus.AI Integration', 'MCP framework integration with Abacus.AI', 'This project demonstrates how to use Model Context Protocol (MCP) with Abacus.AI services.', 'abacus.ai'),
('MCP Framework', 'Core implementation of Model Context Protocol', 'The Model Context Protocol provides structured context sharing for AI/LLM systems with full traceability.', 'framework'),
('Supabase Connector', 'Supabase database connector for MCP', 'This connector enables persistent storage of MCP context data in Supabase tables.', 'supabase');

-- Enable row-level security (but allow access for now)
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.files ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.media ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mcp_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nods_page ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nods_page_section ENABLE ROW LEVEL SECURITY;

-- Create policy to allow all operations for now (update for production)
CREATE POLICY "Allow all for now" ON public.projects FOR ALL TO anon USING (true);
CREATE POLICY "Allow all for now" ON public.chats FOR ALL TO anon USING (true);
CREATE POLICY "Allow all for now" ON public.files FOR ALL TO anon USING (true);
CREATE POLICY "Allow all for now" ON public.media FOR ALL TO anon USING (true);
CREATE POLICY "Allow all for now" ON public.mcp_logs FOR ALL TO anon USING (true);
CREATE POLICY "Allow all for now" ON public.nods_page FOR ALL TO anon USING (true);
CREATE POLICY "Allow all for now" ON public.nods_page_section FOR ALL TO anon USING (true);