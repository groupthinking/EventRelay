"""Autonomous repository research audit input collection and execution."""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

_AUTHORITY_FILES = (
    "AGENTS.md",
    "README.md",
    "docs/REPO_MAP.md",
)

_ORIGINAL_SESSION_CHECKLIST: list[tuple[int, str]] = [
    (1, "Review or analyze an existing GitHub repository"),
    (2, "Pinpoint current use framework for how this repo is operated, and compare if that matches docs"),
    (3, "Code quality, security audit, architecture analysis, startup diligence"),
    (4, "Explore structure"),
    (5, "Trace architecture"),
    (6, "Identify patterns"),
    (7, "Find risks"),
    (8, "Assess business fit"),
    (9, "Grade front end UI/UX"),
    (10, "Grade backend, database, middleware"),
    (11, "Find out if a harness, agents, MCP, RAG, plugins, yt-dlp are in use"),
    (12, "Red flags / discrepancies identified"),
    (13, "GitHub configuration files detected"),
    (14, "Key documentation files"),
    (15, "Report full stack being used vs what is in repo but not being used"),
    (16, "Find the oldest files that haven't been used/touched"),
    (17, "A repo tree visual"),
    (18, "Review how many actions are enabled and what their status is"),
    (19, "Find duplicated documents, MD files, code, configuration"),
    (20, "Look for conflict pathways, configuration, ideas, processes"),
    (21, "Describe what this repo does and how well that purpose is implemented"),
    (22, "Run a user persona walkthrough"),
    (23, "Run a senior engineer persona"),
    (24, "Run an exploit hacker persona"),
    (25, "Find nearest competitors and compare"),
    (26, "Assess whether the solution is presented in the best usable method"),
    (27, "Why would someone need or want to use our services?"),
    (28, "Why can't I just do this in an LLM directly, why should I pay for this?"),
    (29, "Do we have a moat or flywheel?"),
    (30, "Lay out step-by-step strategy with verification before each step"),
    (31, "Place a grade on each item and probable expected change after remediation"),
]


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


def _infer_github_repo_slug(repo_root: Path) -> str | None:
    try:
        remote = subprocess.check_output(
            ["git", "-C", str(repo_root), "config", "--get", "remote.origin.url"],
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$", remote)
    if not match:
        return None
    return f"{match.group('owner')}/{match.group('repo')}"


def collect_live_workflow_health(
    repo_root: Path,
    *,
    github_token: str | None = None,
) -> dict[str, Any]:
    """Collect live workflow run status from GitHub when credentials are available."""
    token = github_token or os.getenv("GITHUB_TOKEN")
    repo_slug = _infer_github_repo_slug(repo_root)
    if not repo_slug:
        return {
            "source": "github-api",
            "status": "unavailable",
            "reason": "Could not infer GitHub repository slug from git remote",
        }
    if not token:
        return {
            "source": "github-api",
            "status": "unavailable",
            "repo_slug": repo_slug,
            "reason": "GITHUB_TOKEN not set; live run health requires GitHub credentials",
        }

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "User-Agent": "EventRelay-Repository-Research-Audit",
    }
    workflows_url = f"https://api.github.com/repos/{repo_slug}/actions/workflows?per_page=100"
    runs_url = f"https://api.github.com/repos/{repo_slug}/actions/runs?per_page=10"
    try:
        with urlopen(Request(workflows_url, headers=headers), timeout=15) as response:
            workflows_payload = json.loads(response.read().decode("utf-8"))
        with urlopen(Request(runs_url, headers=headers), timeout=15) as response:
            runs_payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {
            "source": "github-api",
            "status": "unavailable",
            "repo_slug": repo_slug,
            "reason": str(exc),
        }

    workflows = workflows_payload.get("workflows", [])
    runs = runs_payload.get("workflow_runs", [])
    recent_runs = [
        {
            "name": run.get("name"),
            "path": run.get("path"),
            "status": run.get("status"),
            "conclusion": run.get("conclusion"),
            "event": run.get("event"),
            "head_branch": run.get("head_branch"),
            "html_url": run.get("html_url"),
            "created_at": run.get("created_at"),
        }
        for run in runs
    ]
    failing_workflows = sorted(
        {
            (run.get("path") or run.get("name") or "<unknown>")
            for run in runs
            if run.get("conclusion") not in {None, "success", "skipped"}
        }
    )
    return {
        "source": "github-api",
        "status": "live",
        "repo_slug": repo_slug,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "workflow_count": len(workflows),
        "recent_runs": recent_runs,
        "failing_workflows": failing_workflows,
    }


def _build_original_checklist(
    *,
    live_workflow_health: dict[str, Any],
) -> list[dict[str, Any]]:
    failing_workflows = live_workflow_health.get("failing_workflows", [])
    item_18_status = (
        "handled"
        if live_workflow_health.get("status") == "live"
        else "partially_handled"
    )
    item_18_handling = (
        "Live workflow inventory and recent run status collected from GitHub API"
        + (
            f"; failing workflows: {', '.join(failing_workflows)}."
            if failing_workflows
            else "."
        )
        if item_18_status == "handled"
        else "Workflow inventory is handled from the repository tree; live run status still requires GitHub credentials/MCP at execution time."
    )
    overrides: dict[int, tuple[str, str]] = {
        1: ("handled", "Autonomous audit now analyzes the repository end to end."),
        2: ("handled", "Canonical architecture truth checks repo operation against AGENTS.md, README.md, and REPO_MAP.md."),
        3: ("handled", "Architecture, risk, workflow health, persistence, and product-fit surfaces are covered by the 5 skills."),
        4: ("handled", "Structure is mapped into canonical paths, runtime boundaries, and workflow inventory."),
        5: ("handled", "Architecture interactions and boundaries are traced into audit outputs."),
        6: ("handled", "Patterns are summarized through architecture, persistence, and product-fit skill outputs."),
        7: ("handled", "Risk register captures engineering risks and contradictions."),
        8: ("handled", "Product-positioning-and-buyer-fit covers business fit."),
        9: ("still_needed", "No automated UI/UX grading or persona walkthrough has been implemented."),
        10: ("partially_handled", "Backend/database/middleware structure is mapped, but no numeric grading is emitted."),
        11: ("handled", "Audit covers agents, MCP, harnesses, persistence, and related runtime surfaces."),
        12: ("handled", "Red flags and contradictions are emitted in the risk register and persistence audit."),
        13: ("handled", "GitHub workflow/config files are enumerated via the workflow health skill."),
        14: ("handled", "Authority docs and workflow README are cited directly."),
        15: ("partially_handled", "Current stack is summarized, but a full used-vs-unused inventory is not exhaustive."),
        16: ("still_needed", "Oldest untouched-file analysis has not been automated."),
        17: ("still_needed", "No visual repo tree artifact is generated by the audit."),
        18: (item_18_status, item_18_handling),
        19: ("partially_handled", "Duplication risk is identified, but no exhaustive duplicate-file scan is generated."),
        20: ("partially_handled", "Conflict pathways are partly covered through contradictions and risk items."),
        21: ("handled", "Purpose and implementation fitness are summarized in architecture and product-fit outputs."),
        22: ("still_needed", "User-persona walkthrough is not automated."),
        23: ("still_needed", "Senior engineer persona walkthrough is not automated."),
        24: ("still_needed", "Exploit-hacker persona walkthrough is not automated."),
        25: ("still_needed", "Competitor repo/website comparison is not automated."),
        26: ("still_needed", "Alternate market-delivery analysis is not automated."),
        27: ("handled", "Buyer need is covered in product-fit memo."),
        28: ("handled", "Why not a raw LLM is covered in product-fit memo."),
        29: ("still_needed", "Explicit moat/flywheel analysis is not automated."),
        30: ("handled", "Harness remediation sequence with verification gates covers the step-by-step strategy requirement."),
        31: ("still_needed", "No full grading rubric with projected score deltas is emitted."),
    }
    return [
        {
            "item": item,
            "request": request,
            "status": overrides[item][0],
            "handling": overrides[item][1],
        }
        for item, request in _ORIGINAL_SESSION_CHECKLIST
    ]


def collect_repository_research_inputs(
    repo_root: Path,
    *,
    live_workflow_health: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
    live_workflow_health = live_workflow_health or collect_live_workflow_health(repo_root)

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
                "live_run_health": live_workflow_health,
            },
            "recommended_actions": [
                "Use GitHub credentials or GitHub MCP inspection when live run health is required",
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
        "original_checklist": _build_original_checklist(
            live_workflow_health=live_workflow_health,
        ),
    }


async def run_repository_research_audit(
    repo_root: Path,
    *,
    registry: Any,
    live_workflow_health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Collect repo evidence and execute the repository research harness."""
    audit_inputs = collect_repository_research_inputs(
        repo_root,
        live_workflow_health=live_workflow_health,
    )
    result = await registry.run_repository_research_harness(
        audit_inputs["skill_inputs"],
        harness_evidence_sources=audit_inputs["harness_evidence_sources"],
    )
    result["original_checklist"] = audit_inputs["original_checklist"]
    return result
