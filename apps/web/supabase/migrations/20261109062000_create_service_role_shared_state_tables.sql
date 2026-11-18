-- Shared SQL state for session timelines and agent-to-agent (A2A) messages.
-- Source models: src/youtube_extension/services/shared_sql_state.py (SharedSQLStateStore).
-- Columns, types, nullability, primary keys and indexes match the SQLAlchemy Table
-- definitions exactly (SQLAlchemy emits SERIAL for the integer autoincrement keys and
-- ix_<table>_<column> names for index=True). There are no foreign keys in the models.
-- Idempotent: these tables may already exist in a database where an older build ran
-- metadata.create_all(), so tables, indexes, RLS and grants are all safe to re-apply.
-- Access is service-role only, mirroring public.studio_chats: RLS enabled and forced,
-- no policies, nothing granted to public, anon or authenticated.

create table if not exists public.shared_sessions (
  session_id varchar(255) not null,
  payload text not null,
  version integer not null,
  created_at timestamptz not null,
  updated_at timestamptz not null,
  constraint shared_sessions_pkey primary key (session_id)
);

create table if not exists public.shared_timeline_events (
  id serial not null,
  session_id varchar(255) not null,
  "timestamp" varchar(64) not null,
  summary text not null,
  content text not null,
  constraint shared_timeline_events_pkey primary key (id)
);

create index if not exists ix_shared_timeline_events_session_id on public.shared_timeline_events (session_id);

create table if not exists public.shared_a2a_messages (
  id serial not null,
  sender varchar(255) not null,
  recipient varchar(255) not null,
  conversation_id varchar(255) not null,
  "timestamp" varchar(64) not null,
  content text not null,
  constraint shared_a2a_messages_pkey primary key (id)
);

create index if not exists ix_shared_a2a_messages_conversation_id on public.shared_a2a_messages (conversation_id);

alter table public.shared_sessions enable row level security;
alter table public.shared_sessions force row level security;
revoke all on table public.shared_sessions from public, anon, authenticated;
grant select, insert, update, delete on table public.shared_sessions to service_role;

alter table public.shared_timeline_events enable row level security;
alter table public.shared_timeline_events force row level security;
revoke all on table public.shared_timeline_events from public, anon, authenticated;
grant select, insert, update, delete on table public.shared_timeline_events to service_role;

alter table public.shared_a2a_messages enable row level security;
alter table public.shared_a2a_messages force row level security;
revoke all on table public.shared_a2a_messages from public, anon, authenticated;
grant select, insert, update, delete on table public.shared_a2a_messages to service_role;

-- The serial keys own sequences; inserts need them. Same role boundary as the tables.
revoke all on sequence public.shared_timeline_events_id_seq from public, anon, authenticated;
grant usage, select on sequence public.shared_timeline_events_id_seq to service_role;
revoke all on sequence public.shared_a2a_messages_id_seq from public, anon, authenticated;
grant usage, select on sequence public.shared_a2a_messages_id_seq to service_role;
