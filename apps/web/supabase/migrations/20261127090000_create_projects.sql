-- Plan 005 P2: durable Projects entity. One Project == one canonical YouTube source.
-- Committed as a file only; the operator applies it to remote Supabase manually.
create table public.projects (
  id uuid primary key default gen_random_uuid(),
  owner_subject text not null check (char_length(owner_subject) between 1 and 512),
  source_hash text not null check (source_hash ~ '^[a-f0-9]{64}$'),
  source_url text not null check (char_length(source_url) between 1 and 512),
  title text not null check (char_length(title) between 1 and 160),
  visibility text not null default 'private' check (visibility in ('private', 'shared')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint projects_owner_source_unique unique (owner_subject, source_hash)
);

create index projects_owner_updated_idx on public.projects (owner_subject, updated_at desc, id desc);
create index projects_shared_updated_idx on public.projects (visibility, updated_at desc, id desc) where visibility = 'shared';

alter table public.projects enable row level security;
alter table public.projects force row level security;
revoke all on table public.projects from public, anon, authenticated;
grant select, insert, update, delete on table public.projects to service_role;
