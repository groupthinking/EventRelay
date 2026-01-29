"""
Tests for scripts/nightly_audit_agent.py - Nightly Audit & Remediation Agent
"""
import sys
import tempfile
import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

# Mock the services before importing the agent
sys.modules['youtube_extension.backend.services.health_monitoring_service'] = MagicMock()
sys.modules['youtube_extension.backend.services.database_cleanup_service'] = MagicMock()

from nightly_audit_agent import AuditAgent


class TestAuditAgentInitialization:
    """Test AuditAgent initialization."""

    def test_initialization_dry_run(self):
        """Test agent initialization in dry-run mode."""
        agent = AuditAgent(dry_run=True)
        
        assert agent.dry_run is True
        assert agent.issues == []
        assert agent.remediations == []
        assert agent.fortifications == []
        assert agent.log_dir.is_absolute()
        assert agent.report_dir.is_absolute()

    def test_initialization_live_mode(self):
        """Test agent initialization in live mode."""
        agent = AuditAgent(dry_run=False)
        
        assert agent.dry_run is False
        assert agent.issues == []

    def test_paths_anchored_to_project_root(self):
        """Test that log_dir and report_dir are anchored to project root."""
        agent = AuditAgent()
        
        # Paths should be absolute
        assert agent.log_dir.is_absolute()
        assert agent.report_dir.is_absolute()
        
        # Paths should contain project name
        assert "EventRelay" in str(agent.log_dir)
        assert "EventRelay" in str(agent.report_dir)

    def test_report_dir_created(self):
        """Test that report directory is created on initialization."""
        agent = AuditAgent()
        
        # Report dir should exist
        assert agent.report_dir.exists()
        assert agent.report_dir.is_dir()


class TestLogAnalysis:
    """Test log analysis functionality."""

    @pytest.mark.asyncio
    async def test_analyze_logs_missing_file(self):
        """Test log analysis with missing log file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            agent = AuditAgent()
            agent.log_dir = Path(tmp_dir)
            
            await agent.analyze_logs()
            
            # Should handle gracefully without crashing
            assert True  # If we get here, no exception was raised

    @pytest.mark.asyncio
    async def test_analyze_logs_status_code_400(self):
        """Test that status code 400 is flagged (>= 400 threshold)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            agent = AuditAgent()
            agent.log_dir = Path(tmp_dir)
            
            # Create log file with status 400
            log_file = agent.log_dir / "structured_logs.jsonl"
            log_file.write_text(json.dumps({
                "status_code": 400,
                "endpoint": "/api/test",
                "timestamp": "2026-01-29T12:00:00Z"
            }) + "\n")
            
            await agent.analyze_logs()
            
            # Should flag status 400
            assert len(agent.issues) == 1
            assert agent.issues[0]["type"] == "http_error"
            assert agent.issues[0]["severity"] == "medium"

    @pytest.mark.asyncio
    async def test_analyze_logs_status_code_500(self):
        """Test that status code 500 is flagged as high severity."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            agent = AuditAgent()
            agent.log_dir = Path(tmp_dir)
            
            # Create log file with status 500
            log_file = agent.log_dir / "structured_logs.jsonl"
            log_file.write_text(json.dumps({
                "status_code": 500,
                "endpoint": "/api/error",
                "timestamp": "2026-01-29T12:00:00Z"
            }) + "\n")
            
            await agent.analyze_logs()
            
            # Should flag status 500 as high severity
            assert len(agent.issues) == 1
            assert agent.issues[0]["type"] == "http_error"
            assert agent.issues[0]["severity"] == "high"

    @pytest.mark.asyncio
    async def test_analyze_logs_status_code_200(self):
        """Test that status code 200 is not flagged."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            agent = AuditAgent()
            agent.log_dir = Path(tmp_dir)
            
            # Create log file with status 200
            log_file = agent.log_dir / "structured_logs.jsonl"
            log_file.write_text(json.dumps({
                "status_code": 200,
                "endpoint": "/api/success",
                "timestamp": "2026-01-29T12:00:00Z"
            }) + "\n")
            
            await agent.analyze_logs()
            
            # Should not flag status 200
            assert len(agent.issues) == 0

    @pytest.mark.asyncio
    async def test_analyze_logs_multiple_entries(self):
        """Test log analysis with multiple entries."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            agent = AuditAgent()
            agent.log_dir = Path(tmp_dir)
            
            # Create log file with multiple entries
            log_file = agent.log_dir / "structured_logs.jsonl"
            with open(log_file, 'w') as f:
                f.write(json.dumps({"status_code": 200, "endpoint": "/api/ok"}) + "\n")
                f.write(json.dumps({"status_code": 404, "endpoint": "/api/notfound"}) + "\n")
                f.write(json.dumps({"status_code": 500, "endpoint": "/api/error"}) + "\n")
            
            await agent.analyze_logs()
            
            # Should flag 404 and 500
            assert len(agent.issues) == 2


class TestDatabaseCleanupGating:
    """Test database cleanup gating logic."""

    @pytest.mark.asyncio
    async def test_cleanup_not_triggered_for_http_errors(self):
        """Test that database cleanup is not triggered for HTTP errors."""
        agent = AuditAgent(dry_run=False)
        
        diagnosis = {
            "issue": {"type": "http_error", "severity": "high"},
            "proposed_fix": "Review endpoint logic"
        }
        
        with patch('nightly_audit_agent.run_database_cleanup') as mock_cleanup:
            await agent.ruthless_remediation(diagnosis)
            
            # Database cleanup should not be called for HTTP errors
            mock_cleanup.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_not_triggered_for_non_db_health_issues(self):
        """Test that cleanup is not triggered for non-database health issues."""
        agent = AuditAgent(dry_run=False)
        
        diagnosis = {
            "issue": {
                "type": "health_check",
                "severity": "high",
                "components": ["redis", "external_api"]
            },
            "proposed_fix": "Restart unhealthy services"
        }
        
        with patch('nightly_audit_agent.run_database_cleanup') as mock_cleanup:
            await agent.ruthless_remediation(diagnosis)
            
            # Database cleanup should not be called for non-DB components
            mock_cleanup.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_triggered_for_database_health_issues(self):
        """Test that cleanup IS triggered when database is specifically unhealthy."""
        agent = AuditAgent(dry_run=False)
        
        diagnosis = {
            "issue": {
                "type": "health_check",
                "severity": "high",
                "components": ["database", "redis"]
            },
            "proposed_fix": "Restart unhealthy services"
        }
        
        mock_results = [{"db": "test_db", "status": "cleaned"}]
        with patch('nightly_audit_agent.run_database_cleanup', new_callable=AsyncMock, return_value=mock_results) as mock_cleanup:
            await agent.ruthless_remediation(diagnosis)
            
            # Database cleanup should be called
            mock_cleanup.assert_called_once()
            assert any("database cleanup" in r.lower() for r in agent.remediations)

    @pytest.mark.asyncio
    async def test_cleanup_triggered_for_db_component_case_insensitive(self):
        """Test that cleanup works with case-insensitive DB component names."""
        agent = AuditAgent(dry_run=False)
        
        diagnosis = {
            "issue": {
                "type": "health_check",
                "severity": "high",
                "components": ["Database", "DB_Connection"]
            },
            "proposed_fix": "Restart unhealthy services"
        }
        
        mock_results = []
        with patch('nightly_audit_agent.run_database_cleanup', new_callable=AsyncMock, return_value=mock_results) as mock_cleanup:
            await agent.ruthless_remediation(diagnosis)
            
            # Database cleanup should be called for case variations
            mock_cleanup.assert_called_once()


class TestDryRunMode:
    """Test dry-run mode functionality."""

    @pytest.mark.asyncio
    async def test_dry_run_skips_remediation(self):
        """Test that dry-run mode skips actual remediation."""
        agent = AuditAgent(dry_run=True)
        
        diagnosis = {
            "issue": {
                "type": "health_check",
                "severity": "high",
                "components": ["database"]
            },
            "proposed_fix": "Restart unhealthy services"
        }
        
        with patch('nightly_audit_agent.run_database_cleanup') as mock_cleanup:
            await agent.ruthless_remediation(diagnosis)
            
            # Database cleanup should not be called in dry-run mode
            mock_cleanup.assert_not_called()
            
            # Should have dry-run entry in remediations
            assert len(agent.remediations) > 0
            assert any("[DRY RUN]" in r for r in agent.remediations)

    @pytest.mark.asyncio
    async def test_dry_run_skips_fortification(self):
        """Test that dry-run mode skips fortification."""
        agent = AuditAgent(dry_run=True)
        
        diagnosis = {
            "issue": {"type": "http_error"},
            "preventative_measure": "Add integration test"
        }
        
        await agent.fortify(diagnosis)
        
        # Should have dry-run entry in fortifications
        assert len(agent.fortifications) > 0
        assert any("[DRY RUN]" in f for f in agent.fortifications)


class TestReportGeneration:
    """Test report generation."""

    def test_generate_report_no_issues(self):
        """Test report generation with no issues."""
        agent = AuditAgent()
        
        report = agent.generate_report()
        
        assert "NIGHTLY AUDIT & REMEDIATION REPORT" in report
        assert "ISSUES FOUND:" in report
        assert "None" in report

    def test_generate_report_with_issues(self):
        """Test report generation with issues."""
        agent = AuditAgent()
        agent.issues = [
            {"type": "http_error", "severity": "high", "details": "500 error"}
        ]
        agent.remediations = ["Fixed issue"]
        agent.fortifications = ["Added constraint"]
        
        report = agent.generate_report()
        
        assert "ISSUES FOUND:" in report
        assert "http_error" in report
        assert "REMEDIATIONS EXECUTED:" in report
        assert "Fixed issue" in report
        assert "FORTIFICATIONS APPLIED:" in report
        assert "Added constraint" in report

    def test_generate_report_dry_run_mode(self):
        """Test report generation in dry-run mode."""
        agent = AuditAgent(dry_run=True)
        agent.issues = [{"type": "test", "severity": "low", "details": "test"}]
        
        report = agent.generate_report()
        
        assert "Mode: DRY RUN" in report

    def test_save_report(self):
        """Test saving report to file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            agent = AuditAgent()
            agent.report_dir = Path(tmp_dir)
            
            report = "Test report"
            agent.save_report(report)
            
            # Check that report file was created
            report_files = list(agent.report_dir.glob("audit_report_*.txt"))
            assert len(report_files) == 1
            
            # Check content
            content = report_files[0].read_text()
            assert content == report


class TestAdvisoryLabeling:
    """Test that remediations are properly labeled as advisory."""

    @pytest.mark.asyncio
    async def test_restart_labeled_advisory(self):
        """Test that restart actions are labeled as advisory."""
        agent = AuditAgent(dry_run=False)
        
        diagnosis = {
            "issue": {"type": "health_check"},
            "proposed_fix": "Restart unhealthy services"
        }
        
        # Mock to avoid actual health check components
        diagnosis["issue"]["components"] = []
        
        await agent.ruthless_remediation(diagnosis)
        
        assert any("[ADVISORY]" in r for r in agent.remediations)

    @pytest.mark.asyncio
    async def test_review_labeled_advisory(self):
        """Test that review actions are labeled as advisory."""
        agent = AuditAgent(dry_run=False)
        
        diagnosis = {
            "issue": {"type": "http_error"},
            "proposed_fix": "Review endpoint logic"
        }
        
        await agent.ruthless_remediation(diagnosis)
        
        assert any("[ADVISORY]" in r for r in agent.remediations)

    @pytest.mark.asyncio
    async def test_optimize_labeled_advisory(self):
        """Test that optimization actions are labeled as advisory."""
        agent = AuditAgent(dry_run=False)
        
        diagnosis = {
            "issue": {"type": "high_latency"},
            "proposed_fix": "Optimize query"
        }
        
        await agent.ruthless_remediation(diagnosis)
        
        assert any("[ADVISORY]" in r for r in agent.remediations)
