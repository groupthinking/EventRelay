"""Autonomous repository research audit input collection and execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

_AUTHORITY_FILES = (
    "AGENTS.md",
    "README.md",
    "docs/REPO_MAP.md",
)


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _citation(path: Path, needle: str, repo_root: Path) -> str:
    lines = _read_lines(path)
    for idx, line in enumerate(lines, start=1):
        if needle in line:
            return f"{path.relative_to(repo_root)}:{idx}"
    raise ValueError(f"Missing evidence '{needle}' in {path}")


def _relative(path: Path, repo_root: Path) -> str:
    return str(path.relative_to(repo_root))


def _require_authority_files(repo_root: Path) -> None:
    for relative in _AUTHORITY_FILES:
        path = repo_root / relative
        if not path.is_file():
            raise ValueError(f"Missing authority file: {relative}")


def collect_repository_research_inputs(repo_root: Path) -> dict[str, Any]:
    """Collect repo-backed evidence for the 5 repository research skills."""
    repo_root = repo_root.resolve()
    _require_authority_files(repo_root)

    agents = repo_root / "AGENTS.md"
    readme = repo_root / "README.md"
    repo_map = repo_root / "docs/REPO_MAP.md"
    auth_paths = repo_root / "apps/web/src/lib/auth-paths.ts"
    videopack_store = repo_root / "src/youtube_extension/videopack/store.py"
    backend_main = repo_root / "src/youtube_extension/main.py"
    agent_coordinator = repo_root / "src/agents/mcp_ecosystem_coordinator.py"
    legacy_coordinator = repo_root / "src/mcp/mcp_ecosystem_coordinator.py"
    workflows_dir = repo_root / ".github/workflows"

    harness_evidence_sources = [
        _citation(agents, "Paste a YouTube URL", repo_root),
        _citation(readme, "Paste a YouTube URL", repo_root),
        _citation(repo_map, "UVAI is the public product", repo_root),
    ]

    workflow_files = sorted(path.name for path in workflows_dir.iterdir() if path.is_file())

    skill_inputs = {
        "canonical-architecture-truth": {
            "evidence_sources": [
                _citation(agents, "**UVAI▶**", repo_root),
                _citation(agents, "/dashboard", repo_root),
                _citation(readme, "The product is **UVAI**", repo_root),
                _citation(readme, "/studio", repo_root),
                _citation(repo_map, "Public URL entry and Get Pro", repo_root),
                _citation(repo_map, "Canonical Studio route", repo_root),
            ],
            "canonical_paths": {
                "public_entrypoint": "/",
                "workspace": "/studio",
                "pack_api": "/api/video/pack",
            },
            "legacy_surfaces": ["/dashboard"],
            "public_product_name": "UVAI",
            "internal_runtime_name": "EventRelay",
            "deployment_truth": {
                "production_surface": "apps/web",
                "backend_runtime": "src/youtube_extension",
            },
            "runtime_boundaries": [
                "apps/web",
                "src/youtube_extension",
                "src/agents",
                "mcp-servers",
            ],
            "recommended_actions": [
                "Keep /studio as the canonical workbench surface",
                "Treat EventRelay as the internal runtime name only",
            ],
        },
        "persistence-and-boundary-truth": {
            "evidence_sources": [
                _citation(agents, "Video Pack persistence is **Upstash REST only**", repo_root),
                _citation(readme, "Production Video Pack storage", repo_root),
                _citation(repo_map, "Upstash REST pack persistence", repo_root),
                _citation(auth_paths, "const PUBLIC_API_PREFIXES = [", repo_root),
                _citation(auth_paths, "export function needsAuthentication", repo_root),
                _citation(backend_main, "app.add_middleware(SlowAPIMiddleware)", repo_root),
                _citation(backend_main, "app.add_middleware(SecurityHeadersMiddleware)", repo_root),
                _citation(videopack_store, '"""Filesystem get-or-create store for VideoPack v0.', repo_root),
            ],
            "persistence_truth_map": {
                "video_pack_store": "upstash-rest",
                "backend_sql_state": "sqlite-or-configured-database",
                "filesystem_videopack_store": _relative(videopack_store, repo_root),
            },
            "security_boundary_map": {
                "public_api_policy_source": _relative(auth_paths, repo_root),
                "middleware": [
                    "SlowAPIMiddleware",
                    "SecurityHeadersMiddleware",
                    "APIKeyMiddleware",
                ],
                "public_routes": [
                    "/api/video/pack",
                    "/api/video/pack/frames",
                    "/api/video/sandbox",
                    "/api/pipeline/stream",
                ],
                "gated_pattern": "non-public /api/* routes require authentication",
            },
            "contradictions": [
                {
                    "title": "Web pack contract versus backend filesystem pack store",
                    "detail": "The locked product contract says Video Packs persist via Upstash REST, while backend runtime code still exposes a filesystem VideoPackStore.",
                    "citations": [
                        _citation(agents, "Video Pack persistence is **Upstash REST only**", repo_root),
                        _citation(videopack_store, '"""Filesystem get-or-create store for VideoPack v0.', repo_root),
                    ],
                }
            ],
            "recommended_actions": [
                "Keep Upstash REST as the public Video Pack source of truth",
                "Treat backend filesystem VideoPackStore as an internal/legacy surface unless explicitly promoted",
            ],
        },
        "engineering-risk-and-duplication-audit": {
            "evidence_sources": [
                _citation(agent_coordinator, "class SkillRegistry:", repo_root),
                _citation(legacy_coordinator, "class MCPEcosystemCoordinator:", repo_root),
                _citation(repo_map, "Historical runtime/issue map, not current health", repo_root),
                _citation(repo_map, "Historical March architecture proposal", repo_root),
                _citation(videopack_store, '"""Filesystem get-or-create store for VideoPack v0.', repo_root),
            ],
            "risk_register": [
                {
                    "severity": "high",
                    "title": "Parallel coordinator implementations",
                    "detail": "The repository contains both src/agents and src/mcp coordinator modules, increasing the risk of logic drift.",
                    "citations": [
                        _citation(agent_coordinator, "class SkillRegistry:", repo_root),
                        _citation(legacy_coordinator, "class MCPEcosystemCoordinator:", repo_root),
                    ],
                },
                {
                    "severity": "medium",
                    "title": "Historical docs beside current authority",
                    "detail": "REPO_MAP explicitly preserves historical architecture records, which can drift from the current implementation.",
                    "citations": [
                        _citation(repo_map, "Historical runtime/issue map, not current health", repo_root),
                        _citation(repo_map, "Historical March architecture proposal", repo_root),
                    ],
                },
                {
                    "severity": "medium",
                    "title": "Parallel persistence surfaces",
                    "detail": "Backend filesystem VideoPack storage remains present alongside the locked Upstash REST contract.",
                    "citations": [
                        _citation(agents, "Video Pack persistence is **Upstash REST only**", repo_root),
                        _citation(videopack_store, '"""Filesystem get-or-create store for VideoPack v0.', repo_root),
                    ],
                },
            ],
            "recommended_actions": [
                "Keep canonical coordinator entrypoints explicit in docs and tests",
                "Review historical docs before treating them as implementation truth",
            ],
        },
        "github-ops-and-workflow-health": {
            "evidence_sources": [
                _citation(repo_map, "Workflow catalog", repo_root),
                _citation(repo_root / ".github/workflows/README.md", "## Workflow Catalog", repo_root),
            ],
            "workflow_health_report": {
                "workflow_directory": _relative(workflows_dir, repo_root),
                "workflow_files": workflow_files,
                "workflow_count": len(workflow_files),
                "review_candidates": [
                    name
                    for name in ("verification.yml", "repository-reconciliation.yml")
                    if name in workflow_files
                ],
                "live_run_health": "not-collected-by-local-audit",
            },
            "recommended_actions": [
                "Use GitHub MCP workflow inspection when live run health is required",
                "Review verification.yml and repository-reconciliation.yml for current relevance",
            ],
        },
        "product-positioning-and-buyer-fit": {
            "evidence_sources": [
                _citation(agents, "The differentiator is **action / ship**", repo_root),
                _citation(agents, "| Workflow Pro | **$39/mo** and **$390/yr** |", repo_root),
                _citation(readme, "The differentiator is action and shipping", repo_root),
                _citation(readme, "| Maintain | $199/mo per live product |", repo_root),
            ],
            "product_fit_memo": {
                "positioning": "ship from video evidence",
                "why_not_raw_llm": "UVAI packages evidence-grounded build rails and explicit ship/gate surfaces rather than raw transcription or chat output.",
                "buyer_value": "Users pay for grounded extraction, pack persistence, and action/ship workflow packaging.",
                "pricing": {
                    "workflow_pro_monthly": "$39/mo",
                    "workflow_pro_yearly": "$390/yr",
                    "maintain": "$199/mo",
                    "ship": "per-job quote",
                },
            },
            "recommended_actions": [
                "Keep public messaging focused on action and shipping rather than transcription",
                "Preserve locked pricing and avoid restoring retired EventRelay Pro catalog messaging",
            ],
        },
    }

    return {
        "harness_evidence_sources": harness_evidence_sources,
        "skill_inputs": skill_inputs,
    }


async def run_repository_research_audit(
    repo_root: Path,
    *,
    registry: Any,
) -> dict[str, Any]:
    """Collect repo evidence and execute the repository research harness."""
    audit_inputs = collect_repository_research_inputs(repo_root)
    return await registry.run_repository_research_harness(
        audit_inputs["skill_inputs"],
        harness_evidence_sources=audit_inputs["harness_evidence_sources"],
    )
