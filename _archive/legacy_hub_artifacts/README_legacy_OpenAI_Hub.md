# OpenAI Hub (canonical runtime_root)
Start here for all Codex/OpenAI work. Symlinks only; sources live elsewhere.

## Structure
apps/ • agents/ • projects/ • configs/envs/ • keys/ • backups/

### Projects Directory
- `projects/EventRelay` → consolidated video automation platform (moved from `~/Desktop/EventRelay`)
- `projects/UVAI` → original UVAI umbrella repo (moved from `~/UVAI`)

## Rules
- No secrets in git. Per-project .env only.
- Add new workspaces via bin/hub-add.sh (creates symlink + updates config).
- Validate daily with bin/hub-health.sh.

### Environment Helpers
- Run `projects/UVAI/scripts/export-uvai-root.sh` (or add it to CI) to set `UVAI_ROOT` so path helpers and shared modules resolve correctly.
