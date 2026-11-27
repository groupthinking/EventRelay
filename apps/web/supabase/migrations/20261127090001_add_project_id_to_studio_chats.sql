-- Plan 005 P2: optional link from a Studio chat to its Project. Apply after 20261127090000_create_projects.sql.
alter table public.studio_chats
  add column if not exists project_id uuid references public.projects(id) on delete set null;

create index if not exists studio_chats_owner_project_idx
  on public.studio_chats (owner_subject, project_id, created_at desc)
  where project_id is not null;
