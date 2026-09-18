"""Regression coverage for root CLAUDE.md guidance drift."""

from __future__ import annotations

from pathlib import Path
import unittest


CLAUDE_MD = Path(__file__).resolve().parents[2] / "CLAUDE.md"


def _claude_text() -> str:
    return CLAUDE_MD.read_text()


class ClaudeMdInvariantTests(unittest.TestCase):
    def test_frontend_toolchain_matches_supported_node_constraints(self) -> None:
        text = _claude_text()

        self.assertIn(
            "Node.js >=22; packageManager is npm@10.8.0; root lockfile only",
            text,
        )

    def test_documents_vercel_preview_and_e2e_invariants(self) -> None:
        text = _claude_text()

        self.assertIn("VERCEL_AUTOMATION_BYPASS_SECRET", text)
        self.assertIn("x-vercel-protection-bypass", text)
        self.assertIn("x-vercel-set-bypass-cookie", text)
        self.assertIn("X-EventRelay-Probe: e2e", text)
        self.assertIn("User-Agent: EventRelay-E2E/<run-id>", text)
        self.assertIn(
            "Missing PR previews fail closed. Do not fall back to production.",
            text,
        )


if __name__ == "__main__":
    unittest.main()
