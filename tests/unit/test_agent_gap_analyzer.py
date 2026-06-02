"""Unit tests for services/agents/agent_gap_analyzer.py."""

from __future__ import annotations

import importlib.util
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))


def _load(rel_path: str, canonical: str):
    full = _SRC / rel_path
    spec = importlib.util.spec_from_file_location(canonical, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[canonical] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _load(
    "youtube_extension/services/agents/agent_gap_analyzer.py",
    "youtube_extension.services.agents.agent_gap_analyzer",
)

AgentGap = _mod.AgentGap
AgentRecommendation = _mod.AgentRecommendation
AgentGapAnalyzer = _mod.AgentGapAnalyzer
analyze_agent_gaps = _mod.analyze_agent_gaps


# ===========================================================================
# AgentGap dataclass
# ===========================================================================


class TestAgentGap:
    def test_required_fields(self):
        gap = AgentGap(domain="database", confidence=0.8, reason="Lots of SQL work")
        assert gap.domain == "database"
        assert gap.confidence == 0.8
        assert gap.reason == "Lots of SQL work"

    def test_default_examples_empty_list(self):
        gap = AgentGap(domain="security", confidence=0.5, reason="Auth gaps")
        assert gap.examples == []

    def test_default_frequency_is_one(self):
        gap = AgentGap(domain="devops", confidence=0.6, reason="CI work")
        assert gap.frequency == 1

    def test_custom_examples(self):
        gap = AgentGap(
            domain="database",
            confidence=0.7,
            reason="SQL",
            examples=["example 1", "example 2"],
        )
        assert gap.examples == ["example 1", "example 2"]

    def test_custom_frequency(self):
        gap = AgentGap(domain="database", confidence=0.7, reason="SQL", frequency=5)
        assert gap.frequency == 5

    def test_first_detected_defaults_to_now(self):
        before = datetime.now()
        gap = AgentGap(domain="database", confidence=0.7, reason="SQL")
        after = datetime.now()
        assert before <= gap.first_detected <= after

    def test_last_detected_defaults_to_now(self):
        before = datetime.now()
        gap = AgentGap(domain="database", confidence=0.7, reason="SQL")
        after = datetime.now()
        assert before <= gap.last_detected <= after

    def test_examples_mutable_default_not_shared(self):
        gap1 = AgentGap(domain="a", confidence=0.5, reason="x")
        gap2 = AgentGap(domain="b", confidence=0.5, reason="y")
        gap1.examples.append("hello")
        assert gap2.examples == []


# ===========================================================================
# AgentRecommendation dataclass
# ===========================================================================


class TestAgentRecommendation:
    def _make(self, **kwargs):
        defaults = dict(
            name="database",
            description="Expert guidance for database",
            domains=["postgresql", "sql"],
            tools=["*"],
            expertise_areas=["Schema design"],
            example_scenarios=["Use PostgreSQL"],
            priority="medium",
            confidence=0.85,
        )
        defaults.update(kwargs)
        return AgentRecommendation(**defaults)

    def test_basic_creation(self):
        rec = self._make()
        assert rec.name == "database"
        assert rec.priority == "medium"
        assert rec.confidence == 0.85

    def test_supporting_gaps_defaults_empty(self):
        rec = self._make()
        assert rec.supporting_gaps == []

    def test_supporting_gaps_mutable_default_not_shared(self):
        rec1 = self._make(name="a")
        rec2 = self._make(name="b")
        gap = AgentGap(domain="x", confidence=0.5, reason="y")
        rec1.supporting_gaps.append(gap)
        assert rec2.supporting_gaps == []

    def test_with_gaps(self):
        gap = AgentGap(domain="database", confidence=0.8, reason="SQL work")
        rec = self._make(supporting_gaps=[gap])
        assert len(rec.supporting_gaps) == 1
        assert rec.supporting_gaps[0].domain == "database"

    def test_domains_list(self):
        rec = self._make(domains=["kubernetes", "helm"])
        assert "kubernetes" in rec.domains

    def test_tools_list(self):
        rec = self._make(tools=["read_file", "write_file"])
        assert "read_file" in rec.tools


# ===========================================================================
# AgentGapAnalyzer.__init__
# ===========================================================================


class TestAgentGapAnalyzerInit:
    def test_creates_storage_dir(self, tmp_path):
        storage = tmp_path / "gaps"
        AgentGapAnalyzer(storage_dir=storage)
        assert storage.exists()

    def test_gaps_starts_empty_when_no_file(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        assert analyzer.gaps == {}

    def test_storage_dir_stored(self, tmp_path):
        storage = tmp_path / "gaps"
        analyzer = AgentGapAnalyzer(storage_dir=storage)
        assert analyzer.storage_dir == storage

    def test_default_storage_in_home(self):
        analyzer = AgentGapAnalyzer()
        assert analyzer.storage_dir.exists()

    def test_logger_name(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        assert analyzer.logger.name == "agent_gap_analyzer"


# ===========================================================================
# load_gaps / save_gaps
# ===========================================================================


class TestLoadSaveGaps:
    def test_load_gaps_from_file(self, tmp_path):
        storage = tmp_path / "gaps"
        storage.mkdir()
        gap_data = {
            "database": {
                "domain": "database",
                "confidence": 0.8,
                "reason": "SQL work",
                "examples": ["example1"],
                "frequency": 3,
                "first_detected": "2024-01-01T00:00:00",
                "last_detected": "2024-01-02T00:00:00",
            }
        }
        (storage / "gaps.json").write_text(json.dumps(gap_data))
        analyzer = AgentGapAnalyzer(storage_dir=storage)
        assert "database" in analyzer.gaps
        assert analyzer.gaps["database"].confidence == 0.8
        assert analyzer.gaps["database"].frequency == 3

    def test_load_gaps_missing_file_no_error(self, tmp_path):
        storage = tmp_path / "gaps"
        storage.mkdir()
        # No gaps.json - should not raise
        analyzer = AgentGapAnalyzer(storage_dir=storage)
        assert analyzer.gaps == {}

    def test_save_gaps_creates_file(self, tmp_path):
        storage = tmp_path / "gaps"
        analyzer = AgentGapAnalyzer(storage_dir=storage)
        analyzer.gaps["security"] = AgentGap(
            domain="security", confidence=0.75, reason="Auth issues"
        )
        analyzer.save_gaps()
        gaps_file = storage / "gaps.json"
        assert gaps_file.exists()
        data = json.loads(gaps_file.read_text())
        assert "security" in data

    def test_save_gaps_limits_examples_to_ten(self, tmp_path):
        storage = tmp_path / "gaps"
        analyzer = AgentGapAnalyzer(storage_dir=storage)
        analyzer.gaps["database"] = AgentGap(
            domain="database",
            confidence=0.8,
            reason="SQL",
            examples=[f"example{i}" for i in range(15)],
        )
        analyzer.save_gaps()
        data = json.loads((storage / "gaps.json").read_text())
        assert len(data["database"]["examples"]) == 10

    def test_load_gaps_with_corrupt_file_logs_error(self, tmp_path, caplog):
        storage = tmp_path / "gaps"
        storage.mkdir()
        (storage / "gaps.json").write_text("NOT JSON{{{")
        with caplog.at_level(logging.ERROR, logger="agent_gap_analyzer"):
            analyzer = AgentGapAnalyzer(storage_dir=storage)
        assert analyzer.gaps == {}
        assert any("Failed to load" in r.message for r in caplog.records)

    def test_roundtrip_save_load(self, tmp_path):
        storage = tmp_path / "gaps"
        analyzer = AgentGapAnalyzer(storage_dir=storage)
        analyzer.gaps["devops"] = AgentGap(
            domain="devops",
            confidence=0.9,
            reason="CI pipelines",
            examples=["pipeline 1"],
            frequency=4,
        )
        analyzer.save_gaps()
        # Fresh analyzer reads the saved file
        analyzer2 = AgentGapAnalyzer(storage_dir=storage)
        assert "devops" in analyzer2.gaps
        assert analyzer2.gaps["devops"].confidence == 0.9
        assert analyzer2.gaps["devops"].frequency == 4


# ===========================================================================
# detect_domain_from_context
# ===========================================================================


class TestDetectDomainFromContext:
    def setup_method(self):
        self.analyzer = AgentGapAnalyzer.__new__(AgentGapAnalyzer)
        self.analyzer.logger = logging.getLogger("agent_gap_analyzer")
        self.analyzer.gaps = {}

    def test_detects_infrastructure_from_docker(self):
        result = self.analyzer.detect_domain_from_context("build a docker image")
        assert "infrastructure" in result

    def test_detects_database_from_postgresql(self):
        result = self.analyzer.detect_domain_from_context("postgresql migration")
        assert "database" in result

    def test_detects_security_from_jwt(self):
        result = self.analyzer.detect_domain_from_context("JWT token auth")
        assert "security" in result

    def test_detects_devops_from_github_actions(self):
        result = self.analyzer.detect_domain_from_context("github-actions pipeline")
        assert "devops" in result

    def test_detects_performance_from_optimization(self):
        result = self.analyzer.detect_domain_from_context("caching optimization")
        assert "performance" in result

    def test_detects_multiple_domains(self):
        result = self.analyzer.detect_domain_from_context("docker kubernetes postgresql")
        assert "infrastructure" in result
        assert "database" in result

    def test_empty_context_returns_empty(self):
        result = self.analyzer.detect_domain_from_context("")
        assert result == set()

    def test_unrelated_context_returns_empty(self):
        result = self.analyzer.detect_domain_from_context("hello world coffee")
        assert result == set()

    def test_case_insensitive(self):
        result = self.analyzer.detect_domain_from_context("DOCKER IMAGE")
        assert "infrastructure" in result

    def test_detects_ai_ml_from_pytorch(self):
        result = self.analyzer.detect_domain_from_context("pytorch training loop")
        assert "ai-ml" in result

    def test_detects_mobile_from_android(self):
        result = self.analyzer.detect_domain_from_context("android app development")
        assert "mobile" in result

    def test_detects_blockchain_from_solidity(self):
        result = self.analyzer.detect_domain_from_context("solidity smart contract")
        assert "blockchain" in result


# ===========================================================================
# is_domain_covered
# ===========================================================================


class TestIsDomainCovered:
    def setup_method(self):
        self.analyzer = AgentGapAnalyzer.__new__(AgentGapAnalyzer)
        self.analyzer.logger = logging.getLogger("agent_gap_analyzer")
        self.analyzer.gaps = {}

    def test_python_is_covered(self):
        assert self.analyzer.is_domain_covered("python") is True

    def test_react_is_covered(self):
        assert self.analyzer.is_domain_covered("react") is True

    def test_pytest_is_covered(self):
        assert self.analyzer.is_domain_covered("pytest") is True

    def test_mcp_is_covered(self):
        assert self.analyzer.is_domain_covered("mcp") is True

    def test_markdown_is_covered(self):
        assert self.analyzer.is_domain_covered("markdown") is True

    def test_video_is_covered(self):
        assert self.analyzer.is_domain_covered("video") is True

    def test_docker_is_not_covered(self):
        assert self.analyzer.is_domain_covered("docker") is False

    def test_kubernetes_is_not_covered(self):
        assert self.analyzer.is_domain_covered("kubernetes") is False

    def test_empty_domain_not_covered(self):
        assert self.analyzer.is_domain_covered("completely_unknown_xyz") is False


# ===========================================================================
# record_gap
# ===========================================================================


class TestRecordGap:
    def test_new_gap_created(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.record_gap("database", "Too much SQL", "SQL example", confidence=0.6)
        assert "database" in analyzer.gaps

    def test_new_gap_has_correct_fields(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.record_gap("database", "Too much SQL", "SQL example", confidence=0.6)
        gap = analyzer.gaps["database"]
        assert gap.domain == "database"
        assert gap.confidence == 0.6
        assert gap.reason == "Too much SQL"
        assert "SQL example" in gap.examples

    def test_existing_gap_increments_frequency(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.record_gap("database", "SQL", "example1", confidence=0.5)
        analyzer.record_gap("database", "SQL", "example2", confidence=0.5)
        assert analyzer.gaps["database"].frequency == 2

    def test_existing_gap_increases_confidence(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.record_gap("database", "SQL", "example1", confidence=0.5)
        initial_confidence = analyzer.gaps["database"].confidence
        analyzer.record_gap("database", "SQL", "example2", confidence=0.5)
        assert analyzer.gaps["database"].confidence > initial_confidence

    def test_confidence_capped_at_one(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.record_gap("database", "SQL", "ex", confidence=0.95)
        for _ in range(10):
            analyzer.record_gap("database", "SQL", f"ex{_}", confidence=0.95)
        assert analyzer.gaps["database"].confidence <= 1.0

    def test_duplicate_example_not_added(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.record_gap("database", "SQL", "same_example")
        analyzer.record_gap("database", "SQL", "same_example")
        assert analyzer.gaps["database"].examples.count("same_example") == 1

    def test_new_example_added(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.record_gap("database", "SQL", "example1")
        analyzer.record_gap("database", "SQL", "example2")
        assert "example2" in analyzer.gaps["database"].examples

    def test_persists_to_file(self, tmp_path):
        storage = tmp_path / "gaps"
        analyzer = AgentGapAnalyzer(storage_dir=storage)
        analyzer.record_gap("security", "Auth issues", "JWT example")
        assert (storage / "gaps.json").exists()


# ===========================================================================
# analyze_file_access
# ===========================================================================


class TestAnalyzeFileAccess:
    def test_records_gap_for_uncovered_domain(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.analyze_file_access("infrastructure/docker-compose.yml")
        assert "infrastructure" in analyzer.gaps

    def test_no_gap_for_covered_domain(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        # python is covered
        analyzer.analyze_file_access("src/main.py", "writing python fastapi code")
        assert "infrastructure" not in analyzer.gaps
        assert "database" not in analyzer.gaps

    def test_task_description_included(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.analyze_file_access("config.yml", "helm kubernetes deployment")
        if "infrastructure" in analyzer.gaps:
            gap = analyzer.gaps["infrastructure"]
            assert any("config.yml" in ex for ex in gap.examples)


# ===========================================================================
# analyze_error_pattern
# ===========================================================================


class TestAnalyzeErrorPattern:
    def test_records_gap_for_frequent_errors(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.analyze_error_pattern(
            "ConnectionError", "postgresql database host", frequency=3
        )
        assert "database" in analyzer.gaps

    def test_no_gap_for_low_frequency(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.analyze_error_pattern(
            "ConnectionError", "postgresql database host", frequency=1
        )
        # frequency < 2, so no gap should be recorded
        assert "database" not in analyzer.gaps

    def test_confidence_scales_with_frequency(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.analyze_error_pattern(
            "IOError", "docker kubernetes build", frequency=5
        )
        if "infrastructure" in analyzer.gaps:
            assert analyzer.gaps["infrastructure"].confidence > 0.5

    def test_no_gap_for_covered_domain(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        # python is covered
        analyzer.analyze_error_pattern("SyntaxError", "python fastapi code", frequency=5)
        # All detected domains for "python fastapi code" should be covered
        assert not any(
            d in analyzer.gaps for d in ["infrastructure", "database", "security"]
        )


# ===========================================================================
# get_recommendations
# ===========================================================================


class TestGetRecommendations:
    def _analyzer_with_qualifying_gap(self, tmp_path, domain="database"):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.gaps[domain] = AgentGap(
            domain=domain,
            confidence=0.85,
            reason="SQL work",
            examples=["sql 1", "sql 2", "sql 3"],
            frequency=5,
        )
        return analyzer

    def test_empty_when_no_gaps(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        assert analyzer.get_recommendations() == []

    def test_empty_when_below_confidence_threshold(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.gaps["database"] = AgentGap(
            domain="database", confidence=0.5, reason="SQL", frequency=5
        )
        assert analyzer.get_recommendations() == []

    def test_empty_when_below_frequency_threshold(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.gaps["database"] = AgentGap(
            domain="database", confidence=0.9, reason="SQL", frequency=1
        )
        assert analyzer.get_recommendations() == []

    def test_returns_recommendation_for_qualifying_gap(self, tmp_path):
        analyzer = self._analyzer_with_qualifying_gap(tmp_path)
        recs = analyzer.get_recommendations()
        assert len(recs) == 1
        assert recs[0].name == "database"

    def test_recommendation_has_correct_priority_high(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.gaps["security"] = AgentGap(
            domain="security",
            confidence=0.95,
            reason="Auth",
            examples=["a", "b", "c"],
            frequency=6,
        )
        recs = analyzer.get_recommendations()
        assert recs[0].priority == "high"

    def test_recommendation_has_correct_priority_medium(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.gaps["security"] = AgentGap(
            domain="security",
            confidence=0.85,
            reason="Auth",
            examples=["a", "b", "c"],
            frequency=4,
        )
        recs = analyzer.get_recommendations()
        assert recs[0].priority == "medium"

    def test_recommendation_has_correct_priority_low(self, tmp_path):
        # confidence=0.75 (< 0.8) and frequency=3 => does not meet medium/high thresholds
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.gaps["database"] = AgentGap(
            domain="database",
            confidence=0.75,
            reason="SQL work",
            examples=["sql 1", "sql 2", "sql 3"],
            frequency=3,
        )
        recs = analyzer.get_recommendations()
        assert len(recs) == 1
        assert recs[0].priority == "low"

    def test_sorted_by_priority_then_confidence(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        # High priority
        analyzer.gaps["security"] = AgentGap(
            domain="security", confidence=0.95, reason="Auth", frequency=6
        )
        # Low priority
        analyzer.gaps["database"] = AgentGap(
            domain="database", confidence=0.85, reason="SQL", frequency=5
        )
        recs = analyzer.get_recommendations()
        assert recs[0].name == "security"

    def test_recommendations_use_examples_from_gap(self, tmp_path):
        analyzer = self._analyzer_with_qualifying_gap(tmp_path)
        recs = analyzer.get_recommendations()
        assert "sql 1" in recs[0].example_scenarios

    def test_recommendations_have_supporting_gaps(self, tmp_path):
        analyzer = self._analyzer_with_qualifying_gap(tmp_path)
        recs = analyzer.get_recommendations()
        assert len(recs[0].supporting_gaps) == 1


# ===========================================================================
# _generate_expertise_areas
# ===========================================================================


class TestGenerateExpertiseAreas:
    def setup_method(self, tmp_path=None):
        self.analyzer = AgentGapAnalyzer.__new__(AgentGapAnalyzer)
        self.analyzer.logger = logging.getLogger("agent_gap_analyzer")
        self.analyzer.gaps = {}

    def test_base_areas_always_present(self):
        areas = self.analyzer._generate_expertise_areas("performance")
        assert any("best practices" in a.lower() for a in areas)
        assert any("eventrelay" in a.lower() for a in areas)

    def test_infrastructure_gets_docker_area(self):
        areas = self.analyzer._generate_expertise_areas("infrastructure")
        assert any("Docker" in a for a in areas)

    def test_infrastructure_gets_kubernetes_area(self):
        areas = self.analyzer._generate_expertise_areas("infrastructure")
        assert any("Kubernetes" in a for a in areas)

    def test_database_gets_schema_area(self):
        areas = self.analyzer._generate_expertise_areas("database")
        assert any("schema" in a.lower() for a in areas)

    def test_security_gets_auth_area(self):
        areas = self.analyzer._generate_expertise_areas("security")
        assert any("auth" in a.lower() for a in areas)

    def test_devops_gets_cicd_area(self):
        areas = self.analyzer._generate_expertise_areas("devops")
        assert any("CI/CD" in a or "ci/cd" in a.lower() for a in areas)

    def test_unknown_domain_returns_base_areas_only(self):
        areas = self.analyzer._generate_expertise_areas("unknown_domain")
        # Should have exactly the 5 base areas
        assert len(areas) == 5


# ===========================================================================
# generate_agent_markdown
# ===========================================================================


class TestGenerateAgentMarkdown:
    def _make_rec(self):
        gap = AgentGap(
            domain="database", confidence=0.9, reason="SQL work", examples=["eg1", "eg2"]
        )
        return AgentRecommendation(
            name="database",
            description="Expert database agent",
            domains=["postgresql", "sql"],
            tools=["*"],
            expertise_areas=["Schema design", "Query optimization"],
            example_scenarios=["eg1", "eg2"],
            priority="high",
            confidence=0.9,
            supporting_gaps=[gap],
        )

    def setup_method(self, tmp_path=None):
        self.analyzer = AgentGapAnalyzer.__new__(AgentGapAnalyzer)
        self.analyzer.logger = logging.getLogger("agent_gap_analyzer")
        self.analyzer.gaps = {}

    def test_contains_name_in_frontmatter(self):
        md = self.analyzer.generate_agent_markdown(self._make_rec())
        assert "name: database" in md

    def test_contains_yaml_frontmatter_delimiters(self):
        md = self.analyzer.generate_agent_markdown(self._make_rec())
        assert md.startswith("---")
        assert "---" in md[3:]

    def test_contains_priority_in_frontmatter(self):
        md = self.analyzer.generate_agent_markdown(self._make_rec())
        assert "priority: high" in md

    def test_contains_confidence_in_frontmatter(self):
        md = self.analyzer.generate_agent_markdown(self._make_rec())
        assert "confidence: 0.90" in md

    def test_contains_example_scenarios(self):
        md = self.analyzer.generate_agent_markdown(self._make_rec())
        assert "eg1" in md

    def test_contains_expertise_areas(self):
        md = self.analyzer.generate_agent_markdown(self._make_rec())
        assert "Schema design" in md

    def test_contains_auto_generated_flag(self):
        md = self.analyzer.generate_agent_markdown(self._make_rec())
        assert "auto_generated: true" in md

    def test_contains_integration_section(self):
        md = self.analyzer.generate_agent_markdown(self._make_rec())
        assert "@python-backend" in md

    def test_contains_note_about_auto_generation(self):
        md = self.analyzer.generate_agent_markdown(self._make_rec())
        assert "automatically generated" in md


# ===========================================================================
# export_recommendation
# ===========================================================================


class TestExportRecommendation:
    def _make_rec(self, name="security"):
        return AgentRecommendation(
            name=name,
            description="Security agent",
            domains=["auth", "jwt"],
            tools=["*"],
            expertise_areas=["Auth best practices"],
            example_scenarios=["JWT issues"],
            priority="high",
            confidence=0.9,
        )

    def test_creates_file(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        rec = self._make_rec()
        filepath = analyzer.export_recommendation(rec, output_dir=tmp_path / "recs")
        assert filepath.exists()

    def test_file_has_correct_name(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        rec = self._make_rec(name="security")
        filepath = analyzer.export_recommendation(rec, output_dir=tmp_path / "recs")
        assert filepath.name == "security.agent.md"

    def test_file_contains_markdown(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        rec = self._make_rec()
        filepath = analyzer.export_recommendation(rec, output_dir=tmp_path / "recs")
        content = filepath.read_text()
        assert "name: security" in content

    def test_default_output_dir_used_when_none(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        rec = self._make_rec()
        filepath = analyzer.export_recommendation(rec)
        assert filepath.exists()
        assert "recommendations" in str(filepath)

    def test_creates_output_dir_if_missing(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        rec = self._make_rec()
        output_dir = tmp_path / "new_recs" / "nested"
        analyzer.export_recommendation(rec, output_dir=output_dir)
        assert output_dir.exists()


# ===========================================================================
# generate_summary_report
# ===========================================================================


class TestGenerateSummaryReport:
    def test_report_contains_header(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        report = analyzer.generate_summary_report()
        assert "Agent Gap Analysis Report" in report

    def test_report_shows_zero_gaps(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        report = analyzer.generate_summary_report()
        assert "Total Gaps Detected**: 0" in report

    def test_report_includes_gap_table(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.gaps["security"] = AgentGap(
            domain="security", confidence=0.6, reason="auth", frequency=2
        )
        report = analyzer.generate_summary_report()
        assert "security" in report

    def test_report_shows_monitoring_status(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.gaps["devops"] = AgentGap(
            domain="devops", confidence=0.5, reason="CI", frequency=1
        )
        report = analyzer.generate_summary_report()
        assert "Monitoring" in report

    def test_report_shows_recommended_status_for_qualifying_gap(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.gaps["database"] = AgentGap(
            domain="database",
            confidence=0.9,
            reason="SQL",
            examples=["ex1", "ex2", "ex3"],
            frequency=5,
        )
        report = analyzer.generate_summary_report()
        assert "Recommended" in report

    def test_report_no_recommendations_message(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        report = analyzer.generate_summary_report()
        assert "No New Agents Recommended" in report

    def test_report_shows_recommended_agents_section(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        analyzer.gaps["security"] = AgentGap(
            domain="security",
            confidence=0.95,
            reason="Auth",
            examples=["a", "b", "c"],
            frequency=6,
        )
        report = analyzer.generate_summary_report()
        assert "Recommended New Agents" in report

    def test_report_has_generated_date(self, tmp_path):
        analyzer = AgentGapAnalyzer(storage_dir=tmp_path / "gaps")
        report = analyzer.generate_summary_report()
        assert "Generated:" in report


# ===========================================================================
# analyze_agent_gaps convenience function
# ===========================================================================


class TestAnalyzeAgentGapsFunction:
    def test_returns_analyzer_instance(self):
        result = analyze_agent_gaps()
        assert isinstance(result, AgentGapAnalyzer)

    def test_returns_fresh_instance_each_time(self):
        a1 = analyze_agent_gaps()
        a2 = analyze_agent_gaps()
        assert a1 is not a2
