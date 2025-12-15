# UVAI Consolidation Plan

## Unique Assets to Preserve
- **Contracts & Governance** – `00_FOUNDATION/` holds compliance contracts and governance policies referenced by agents (e.g. `UVAI-USC-001`). These should move into a shared `contracts/` package and be loaded via configurable paths.
- **Agent Templates & Registry** – `src/agents/templates/`, `src/agents/registry/`, and `src/agents/README.md` document the umbrella architecture; fold these into EventRelay’s `services/agents` docs to keep lineage clear.
- **R&D Experiments** – `src/intelligence/Grok-Claude-Hybrid-Deployment/` and other exploratory directories capture hybrid workflows not present in EventRelay; keep them under an `archive/` or `research/` namespace.
- **Workflow Specs** – YAML definitions in `src/agents/workflows/` formalise the intake→analysis→action pipeline. Maintain them as source-of-truth and sync with EventRelay’s workflow docs.

## Shared Module Targets
- `src/shared/contracts/` – store YAML contracts with helper loaders.
- `src/shared/agents/` – centralise templates, registries, and DTOs.
- `src/shared/mcp/` – reuse the consolidated MCP video processor and coordinator logic.
- `src/shared/rnd/` – optional module for archived experiments with clear “unsupported” warnings.

## Migration Steps
1. **Path Abstraction** – replace hard-coded `/Users/garvey/UVAI/...` references with `UVAI_ROOT` (env var) or configuration helper.
2. **Package Extraction** – move contracts, templates, and registry code into the shared namespaces above; update imports in both EventRelay and UVAI.
3. **Docs Update** – merge UVAI architectural docs into hub knowledge base, linking offshoot projects back to the UVAI vision.
4. **Repository Relocation** – once code references are relative/config-driven, move the UVAI repo into `Dev/OpenAI_Hub/projects/UVAI` and adjust hub indexes.
