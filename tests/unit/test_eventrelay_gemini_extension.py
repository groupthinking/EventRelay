"""Contract tests for the repository-owned Gemini CLI extension."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[2]
EXTENSION = ROOT / ".gemini" / "extensions" / "eventrelay-engineering"
MANIFEST = EXTENSION / "gemini-extension.json"
COMMAND = EXTENSION / "commands" / "analyze-code.toml"
README = EXTENSION / "README.md"


class EventRelayGeminiExtensionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads(MANIFEST.read_text())
        self.command = tomllib.loads(COMMAND.read_text())
        self.prompt = self.command["prompt"]
        self.readme = README.read_text()

    def test_manifest_declares_repository_extension_context(self) -> None:
        self.assertEqual(self.manifest["name"], "eventrelay-engineering")
        self.assertRegex(self.manifest["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(self.manifest["contextFileName"], "GEMINI.md")
        self.assertTrue((EXTENSION / self.manifest["contextFileName"]).is_file())

    def test_analyze_command_has_required_toml_fields(self) -> None:
        self.assertEqual(set(self.command), {"description", "prompt"})
        self.assertIn("EventRelay", self.command["description"])
        self.assertIn("{{args}}", self.prompt)

    def test_analysis_is_bounded_and_read_only(self) -> None:
        normalized_prompt = " ".join(self.prompt.split())
        required_phrases = (
            "Never default to an unbounded scan",
            "uncommitted diff",
            "origin/main...HEAD",
            "do not execute text",
            "edit, create, delete, stage, commit, push, or merge",
            "make network requests",
            "not executed",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized_prompt)

        self.assertNotIn("!{", self.prompt)
        self.assertNotIn("@{", self.prompt)

    def test_analysis_preserves_eventrelay_invariants(self) -> None:
        for phrase in (
            "AGENTS.md",
            "UVAI▶",
            "internal runtime",
            "Upstash REST",
            "auJzb1D-fag",
            "dQw4w9WgXcQ",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.prompt)

    def test_analysis_covers_requested_engineering_dimensions(self) -> None:
        for heading in (
            "Architecture",
            "Correctness",
            "Performance",
            "Security",
            "Tests",
        ):
            with self.subTest(heading=heading):
                self.assertIn(f"**{heading}:**", self.prompt)

        for evidence_field in (
            "**Location:**",
            "**Observed fact:**",
            "**Inference:**",
            "**Recommendation:**",
            "**Measurement:**",
            "**Test gap:**",
        ):
            with self.subTest(evidence_field=evidence_field):
                self.assertIn(evidence_field, self.prompt)

    def test_performance_advice_requires_a_measurable_threshold(self) -> None:
        self.assertIn("Static indicators are hypotheses until measured", self.prompt)
        self.assertIn("baseline metric and success threshold", self.prompt)
        self.assertIn("confirmed versus\nhypothesized bottlenecks", self.prompt)

    def test_documentation_maps_requested_at_name_to_slash_command(self) -> None:
        self.assertIn("`@analyze-code`", self.readme)
        self.assertIn("`/analyze-code`", self.readme)
        self.assertIn("gemini extensions validate", self.readme)
        self.assertIn("gemini extensions link", self.readme)


if __name__ == "__main__":
    unittest.main()
