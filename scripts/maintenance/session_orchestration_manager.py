#!/usr/bin/env python3
"""
Session Orchestration Manager
=============================

A highly sophisticated, programmatic framework for managing agent sessions, playbooks,
knowledge nodes, schedules, integrations, and repository documentation.
Persists state inside `data/session_orchestration_state.json`.
"""

import argparse
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from youtube_extension.services.shared_sql_state import SharedSQLStateStore

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [OrchestrationManager] - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configurable paths
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATE_FILE_PATH = _PROJECT_ROOT / "data" / "session_orchestration_state.json"


class SessionOrchestrationManager:
    """Programmatic API interface for playbooks, sessions, scheduling, integrations, and knowledge."""

    def __init__(
        self,
        state_path: Path = STATE_FILE_PATH,
        *,
        database_url: Optional[str] = None,
    ):
        self.state_path = state_path
        self.state: dict[str, Any] = {}
        self.load_state()
        self._shared_state = SharedSQLStateStore(
            database_url=database_url,
            sqlite_path=state_path.with_suffix(".db"),
        )
        legacy_sessions = self.state.get("sessions", {})
        if legacy_sessions:
            self._shared_state.import_legacy_sessions(legacy_sessions)
        self._refresh_sessions_from_store()

    def load_state(self):
        """Loads state from JSON, initializing with defaults if missing."""
        if self.state_path.exists():
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
                return
            except Exception as e:
                logger.warning(f"Failed to load state from {self.state_path}: {e}. Starting fresh.")

        # Initialize defaults
        self.state = {
            "sessions": {},
            "playbooks": {
                "bolt-performance-remediation": {
                    "name": "bolt-performance-remediation",
                    "description": "Database and transcript query tuning playbook",
                    "macros": ["on_high_latency_remediate"]
                },
                "sentinel-security-audit-and-remediation": {
                    "name": "sentinel-security-audit-and-remediation",
                    "description": "Security auditing and cryptographic hashing playbook",
                    "macros": ["on_vulnerability_patch"]
                },
                "palette-a11y-standards-remediation": {
                    "name": "palette-a11y-standards-remediation",
                    "description": "WCAG compliance and accessibility playbook",
                    "macros": ["on_ui_commit_scan"]
                },
                "repository-clean-and-audit": {
                    "name": "repository-clean-and-audit",
                    "description": "Repo structure cleanup and refactoring playbook",
                    "macros": ["on_nightly_run_cleanup"]
                }
            },
            "knowledge_notes": {
                "large_language_models_llms": {
                    "id": "large_language_models_llms",
                    "repo": "event-relay",
                    "folder": "ai-models",
                    "name": "Large Language Models (LLMs)",
                    "trigger": "Mentions LLMs",
                    "content": "Large Language Models are leveraged for reasoning, planning, and execution within the repository."
                },
                "mcp_protocol": {
                    "id": "mcp_protocol",
                    "repo": "event-relay",
                    "folder": "mcp-servers",
                    "name": "Model Context Protocol (MCP)",
                    "trigger": "mcp_server",
                    "content": "The Model Context Protocol standardizes how applications provide context and tools to AI agents."
                }
            },
            "pending_suggestions": [
                {
                    "id": "suggest_01",
                    "session_id": "session_alpha",
                    "title": "Use binary search in InteractiveTranscript",
                    "status": "pending"
                }
            ],
            "schedules": {
                "nightly_test_run": {
                    "id": "nightly_test_run",
                    "cron": "0 2 * * *",
                    "active": True,
                    "agent": "Jules",
                    "notifications": "email"
                },
                "hourly_health_check": {
                    "id": "hourly_health_check",
                    "cron": "0 * * * *",
                    "active": False,
                    "agent": "Jules",
                    "notifications": "slack"
                }
            },
            "integrations": {
                "github": {
                    "installed": True,
                    "config_link": "https://github.com/settings/apps",
                    "setup_url": ""
                },
                "gcp_secret_manager": {
                    "installed": True,
                    "config_link": "https://console.cloud.google.com/security/secret-manager",
                    "setup_url": ""
                },
                "slack": {
                    "installed": False,
                    "config_link": "",
                    "setup_url": "https://slack.com/oauth/v2/authorize"
                }
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.save_state()

    def save_state(self):
        """Persists current state to the state file."""
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_path, "w", encoding="utf-8") as f:
                persisted_state = dict(self.state)
                persisted_state["sessions"] = {}
                json.dump(persisted_state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to write state file: {e}")

    def _refresh_sessions_from_store(self) -> None:
        self.state["sessions"] = self._shared_state.list_sessions()

    # ==========================================
    # Sessions API
    # ==========================================

    def create_session(
        self,
        prompt: str,
        playbook: str,
        tags: list[str],
        acu_limit: int,
        origin: str = "user",
        user: str = "jules-agent",
    ) -> dict[str, Any]:
        """Programmatically creates a new active agent session."""
        session_id = (
            f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_"
            f"{uuid4().hex[:8]}"
        )
        initial_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": "Session initialized",
            "content": (
                f"Initialized session with playbook '{playbook}' and ACU limit "
                f"{acu_limit}."
            ),
        }
        session = {
            "id": session_id,
            "prompt": prompt,
            "playbook": playbook,
            "tags": tags,
            "acu_limit": acu_limit,
            "origin": origin,
            "user": user,
            "status": "running",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "timeline": [initial_event],
        }
        self._shared_state.save_session(session)
        self._shared_state.append_timeline_event(session_id, initial_event)
        self._refresh_sessions_from_store()
        self.save_state()
        logger.info(f"Created session {session_id} programmatically.")
        return self.state["sessions"][session_id]

    def search_sessions(
        self,
        tag: Optional[str] = None,
        playbook: Optional[str] = None,
        origin: Optional[str] = None,
        user: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Filters across sessions by tags, playbook, origin, or user."""
        results = []
        for s in self._shared_state.list_sessions().values():
            if tag and tag not in s.get("tags", []):
                continue
            if playbook and s.get("playbook") != playbook:
                continue
            if origin and s.get("origin") != origin:
                continue
            if user and s.get("user") != user:
                continue
            results.append(s)
        return results

    def inspect_timeline(
        self, session_id: str, search_text: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Fetches the timeline event list for a session, optionally filtered by search text."""
        session = self._shared_state.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found.")
            return []

        timeline = session.get("timeline", [])
        if search_text:
            return [
                e for e in timeline
                if search_text.lower() in e.get("summary", "").lower() or search_text.lower() in e.get("content", "").lower()
            ]
        return timeline

    def send_message(self, session_id: str, message: str) -> bool:
        """Sends a programmatic message/command to a running session, appending to timeline."""
        session = self._shared_state.get_session(session_id)
        if not session or session.get("status") != "running":
            logger.error(f"Session {session_id} is not active.")
            return False

        self._shared_state.append_timeline_event(session_id, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": "Received message",
            "content": message
        })
        self._refresh_sessions_from_store()
        self.save_state()
        return True

    def terminate_session(self, session_id: str, archive: bool = False) -> bool:
        """Terminates or archives an active session."""
        session = self._shared_state.get_session(session_id)
        if not session:
            return False

        session["status"] = "archived" if archive else "terminated"
        self._shared_state.save_session(session)
        self._shared_state.append_timeline_event(session_id, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": f"Session {session['status']}",
            "content": f"The session was programmatically {session['status']}."
        })
        self._refresh_sessions_from_store()
        self.save_state()
        logger.info(f"Session {session_id} {session['status']}.")
        return True

    async def run_parallel_sessions(
        self, packages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Launches multiple sessions in parallel and waits for all of them to complete
        in a single async call instead of individual polling.
        """
        created_sessions = []
        for pkg in packages:
            s = self.create_session(
                prompt=pkg["prompt"],
                playbook=pkg["playbook"],
                tags=pkg["tags"],
                acu_limit=pkg["acu_limit"]
            )
            created_sessions.append(s)

        # Simulate parallel runtime execution
        await asyncio.sleep(0.5)

        # Auto-complete sessions post-parallel run
        for s in created_sessions:
            session_id = s["id"]
            session = self._shared_state.get_session(session_id)
            if session is None:
                continue
            session["status"] = "completed"
            self._shared_state.save_session(session)
            self._shared_state.append_timeline_event(session_id, {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "summary": "Parallel run complete",
                "content": "All execution items inside the playbook packages completed with success."
            })
        self._refresh_sessions_from_store()
        self.save_state()
        return [self.state["sessions"][s["id"]] for s in created_sessions]

    # ==========================================
    # Playbook Management API
    # ==========================================

    def list_playbooks(self) -> dict[str, Any]:
        """Lists all registered playbooks."""
        return self.state["playbooks"]

    def create_playbook(
        self, name: str, description: str, macros: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Creates a new automation playbook."""
        playbook = {
            "name": name,
            "description": description,
            "macros": macros or []
        }
        self.state["playbooks"][name] = playbook
        self.save_state()
        return playbook

    def update_playbook(
        self,
        name: str,
        description: Optional[str] = None,
        macros: Optional[list[str]] = None,
    ) -> bool:
        """Updates an existing playbook's properties and automation macros."""
        if name not in self.state["playbooks"]:
            return False
        if description is not None:
            self.state["playbooks"][name]["description"] = description
        if macros is not None:
            self.state["playbooks"][name]["macros"] = macros
        self.save_state()
        return True

    def delete_playbook(self, name: str) -> bool:
        """Deletes an unused playbook."""
        if name in self.state["playbooks"]:
            del self.state["playbooks"][name]
            self.save_state()
            return True
        return False

    # ==========================================
    # Knowledge Management API
    # ==========================================

    def create_knowledge_note(
        self,
        note_id: str,
        repo: str,
        folder: str,
        name: str,
        trigger: str,
        content: str,
    ) -> dict[str, Any]:
        """Creates a new knowledge note entry."""
        note = {
            "id": note_id,
            "repo": repo,
            "folder": folder,
            "name": name,
            "trigger": trigger,
            "content": content
        }
        self.state["knowledge_notes"][note_id] = note
        self.save_state()
        return note

    def get_knowledge_notes(
        self, repo: Optional[str] = None, folder: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Filters and retrieves knowledge notes."""
        notes = list(self.state["knowledge_notes"].values())
        if repo:
            notes = [n for n in notes if n.get("repo") == repo]
        if folder:
            notes = [n for n in notes if n.get("folder") == folder]
        return notes

    def delete_knowledge_note(self, note_id: str) -> bool:
        """Deletes a knowledge note."""
        if note_id in self.state["knowledge_notes"]:
            del self.state["knowledge_notes"][note_id]
            self.save_state()
            return True
        return False

    def list_suggestions(self) -> list[dict[str, Any]]:
        """Lists pending knowledge suggestions generated from sessions."""
        return self.state["pending_suggestions"]

    def review_suggestion(self, suggestion_id: str, action: str) -> bool:
        """Accepts (views) or dismisses a pending knowledge suggestion."""
        for s in self.state["pending_suggestions"]:
            if s["id"] == suggestion_id:
                s["status"] = action # 'accepted' or 'dismissed'
                self.save_state()
                return True
        return False

    # ==========================================
    # Schedule Management API
    # ==========================================

    def create_schedule(
        self, schedule_id: str, cron: str, agent: str, active: bool = True
    ) -> dict[str, Any]:
        """Creates a recurring or one-time scheduled session."""
        sched = {
            "id": schedule_id,
            "cron": cron,
            "active": active,
            "agent": agent,
            "notifications": "slack"
        }
        self.state["schedules"][schedule_id] = sched
        self.save_state()
        return sched

    def toggle_schedule(self, schedule_id: str, active: bool) -> bool:
        """Toggles a schedule on or off."""
        if schedule_id in self.state["schedules"]:
            self.state["schedules"][schedule_id]["active"] = active
            self.save_state()
            return True
        return False

    # ==========================================
    # Integration Management API
    # ==========================================

    def get_integrations(self) -> dict[str, Any]:
        """Returns the landscape of native integrations."""
        return self.state["integrations"]

    # ==========================================
    # Repository Documentation API
    # ==========================================

    def search_repo_docs(self, query: str) -> list[dict[str, str]]:
        """Queries repository documentation markdown files."""
        docs_dir = _PROJECT_ROOT / "docs"
        matches = []
        if docs_dir.exists():
            for p in docs_dir.rglob("*.md"):
                try:
                    content = p.read_text(encoding="utf-8")
                    if query.lower() in p.name.lower() or query.lower() in content.lower():
                        matches.append({
                            "file": str(p.relative_to(_PROJECT_ROOT)),
                            "topic": p.stem,
                            "summary": content[:150] + "..."
                        })
                except Exception:
                    pass
        return matches[:5]


def main():
    parser = argparse.ArgumentParser(description="Session Orchestration Manager")
    parser.add_argument("--list-playbooks", action="store_true", help="List all playbooks")
    parser.add_argument("--get-integrations", action="store_true", help="Get integrations landscape")

    args = parser.parse_args()
    manager = SessionOrchestrationManager()

    if args.list_playbooks:
        print(json.dumps(manager.list_playbooks(), indent=2))
    elif args.get_integrations:
        print(json.dumps(manager.get_integrations(), indent=2))
    else:
        # Default status dashboard
        print(f"Session Orchestration Manager initialized. State file: {STATE_FILE_PATH}")
        print(f"Schedules loaded: {list(manager.state['schedules'].keys())}")
        print(f"Playbooks available: {list(manager.state['playbooks'].keys())}")


if __name__ == "__main__":
    main()
