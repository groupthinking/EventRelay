# Repository Guidelines

## Project Structure & Module Organization
Backend FastAPI services live in `src/youtube_extension/`, including the agent orchestration layer under `services/agents/` and intelligence helpers. React dashboards and static assets sit in `frontend/`. Automation, deployment, and experiments live respectively in `development/`, `infrastructure/`, and `scripts/`. Python tests mirror runtime code inside `tests/`, while React specs live in `frontend/src/__tests__/`.

## Build, Test, and Development Commands
- `pip install -e .[dev,youtube,ml]`: install all backend extras for local development.
- `uvicorn youtube_extension.main:app --reload --port 8000`: boot the API with hot reload.
- `npm install` then `npm start` from `frontend/`: set up and run the dashboard during local work.
- `npm run build`: produce production bundles for the UI.

## Coding Style & Naming Conventions
Python uses 4-space indentation, type hints, snake_case functions, and PascalCase classes. Run `black .`, `isort .`, and `ruff check .` before opening a PR, and type-check core packages with `mypy src/youtube_extension`. Frontend code follows the Create React App defaults; components use PascalCase filenames and hooks stay in camelCase (for example `useProjectData.ts`).

## Testing Guidelines
Run `pytest` for the backend and agents; scope to suites with `pytest tests/integration -k video` when iterating. Aim for ≥80% coverage on new modules and add fixtures under `tests/fixtures/` for new data contracts. For UI, execute `npm test -- --watch=false` to get deterministic output and keep accessibility checks passing.

## Commit & Pull Request Guidelines
Use imperative commit subjects (for example `Add realtime status channel`) and keep related changes together. Every PR should explain motivation, implementation, and testing, link to Linear/Jira issues, and attach UI screenshots or API traces when behaviour changes. Call out any skipped tests and note `pytest`/`npm test`/lint results explicitly.

## Agent-Specific Practices
New agents belong in `development/agents/`; reuse existing mixins instead of duplicating API calls. Document triggers and queues in a short README snippet and wire the agent through `src/youtube_extension/services/agents/` with feature flags so environments can toggle behaviour safely.
