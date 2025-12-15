"""
Tests for Agent Gap Analyzer
=============================

Tests the agent gap detection and recommendation system including:
- Gap detection logic
- Recommendation generation
- Template creation
- CLI commands
- Edge cases and error handling
"""

import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

# Import the modules to test
import sys
agent_module_path = Path(__file__).parent.parent / "src" / "youtube_extension" / "services" / "agents"
sys.path.insert(0, str(agent_module_path))

from agent_gap_analyzer import (
    AgentGapAnalyzer,
    AgentGap,
    AgentRecommendation
)


class TestAgentGap:
    """Test AgentGap dataclass."""

    def test_agent_gap_creation(self):
        """Test creating an AgentGap instance."""
        gap = AgentGap(
            domain="infrastructure",
            confidence=0.75,
            reason="Frequent Kubernetes work",
            examples=["k8s/deployment.yaml"]
        )
        
        assert gap.domain == "infrastructure"
        assert gap.confidence == 0.75
        assert gap.reason == "Frequent Kubernetes work"
        assert len(gap.examples) == 1
        assert gap.frequency == 1

    def test_agent_gap_defaults(self):
        """Test AgentGap default values."""
        gap = AgentGap(
            domain="database",
            confidence=0.5,
            reason="Database work"
        )
        
        assert gap.examples == []
        assert gap.frequency == 1
        assert isinstance(gap.first_detected, datetime)
        assert isinstance(gap.last_detected, datetime)


class TestAgentRecommendation:
    """Test AgentRecommendation dataclass."""

    def test_recommendation_creation(self):
        """Test creating an AgentRecommendation instance."""
        rec = AgentRecommendation(
            name="infrastructure",
            description="Infrastructure expert",
            domains=["docker", "kubernetes"],
            tools=["*"],
            expertise_areas=["K8s", "Docker"],
            example_scenarios=["Deploy app"],
            priority="high",
            confidence=0.85
        )
        
        assert rec.name == "infrastructure"
        assert rec.priority == "high"
        assert rec.confidence == 0.85
        assert len(rec.domains) == 2
        assert len(rec.supporting_gaps) == 0


class TestAgentGapAnalyzer:
    """Test AgentGapAnalyzer class."""

    def test_analyzer_initialization(self):
        """Test analyzer initialization with temp storage."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            analyzer = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            
            assert analyzer.storage_dir.exists()
            assert isinstance(analyzer.gaps, dict)
            assert len(analyzer.gaps) == 0

    def test_detect_domain_from_context(self):
        """Test domain detection from file paths and content."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            analyzer = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            
            # Test infrastructure detection
            domains = analyzer.detect_domain_from_context(
                "infrastructure/kubernetes/deployment.yaml"
            )
            assert "infrastructure" in domains
            
            # Test database detection
            domains = analyzer.detect_domain_from_context(
                "database/migrations/001_create_tables.sql"
            )
            assert "database" in domains
            
            # Test security detection
            domains = analyzer.detect_domain_from_context(
                "src/auth/oauth.py - implementing JWT authentication"
            )
            assert "security" in domains

    def test_is_domain_covered(self):
        """Test checking if domain is covered by existing agents."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            analyzer = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            
            # Existing domains should be covered
            assert analyzer.is_domain_covered("python")
            assert analyzer.is_domain_covered("fastapi")
            assert analyzer.is_domain_covered("react")
            assert analyzer.is_domain_covered("testing")
            
            # New domains should not be covered
            assert not analyzer.is_domain_covered("infrastructure")
            assert not analyzer.is_domain_covered("database")
            assert not analyzer.is_domain_covered("blockchain")

    def test_record_gap(self):
        """Test recording a gap in coverage."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            analyzer = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            
            # Record first gap
            analyzer.record_gap(
                domain="infrastructure",
                reason="Kubernetes work",
                example="k8s/deployment.yaml",
                confidence=0.5
            )
            
            assert "infrastructure" in analyzer.gaps
            gap = analyzer.gaps["infrastructure"]
            assert gap.confidence == 0.5
            assert gap.frequency == 1
            assert len(gap.examples) == 1
            
            # Record same domain again
            analyzer.record_gap(
                domain="infrastructure",
                reason="Kubernetes work",
                example="k8s/service.yaml",
                confidence=0.5
            )
            
            gap = analyzer.gaps["infrastructure"]
            assert gap.frequency == 2
            assert gap.confidence == 0.6  # Increased by 0.1
            assert len(gap.examples) == 2

    def test_analyze_file_access(self):
        """Test analyzing file access patterns."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            analyzer = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            
            # Analyze infrastructure files
            analyzer.analyze_file_access(
                "infrastructure/k8s/deployment.yaml",
                "Deploying application"
            )
            
            assert "infrastructure" in analyzer.gaps
            
            # Analyze database files
            analyzer.analyze_file_access(
                "database/migrations/001_users.sql",
                "Creating user table"
            )
            
            assert "database" in analyzer.gaps

    def test_analyze_error_pattern(self):
        """Test analyzing error patterns."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            analyzer = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            
            # Analyze database error
            analyzer.analyze_error_pattern(
                "DatabaseConnectionError",
                "PostgreSQL connection timeout",
                frequency=3
            )
            
            assert "database" in analyzer.gaps
            gap = analyzer.gaps["database"]
            assert gap.frequency >= 1
            assert gap.confidence >= 0.5

    def test_get_recommendations_empty(self):
        """Test getting recommendations when no gaps meet threshold."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            analyzer = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            
            # Record gap below threshold
            analyzer.record_gap(
                domain="infrastructure",
                reason="Test",
                example="test.yaml",
                confidence=0.5
            )
            
            recommendations = analyzer.get_recommendations()
            assert len(recommendations) == 0

    def test_get_recommendations_with_valid_gaps(self):
        """Test getting recommendations when gaps meet threshold."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            analyzer = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            
            # Record gaps that meet threshold
            for i in range(4):
                analyzer.record_gap(
                    domain="infrastructure",
                    reason="Kubernetes work",
                    example=f"k8s/file{i}.yaml",
                    confidence=0.5
                )
            
            recommendations = analyzer.get_recommendations()
            assert len(recommendations) >= 1
            
            rec = recommendations[0]
            assert rec.name == "infrastructure"
            assert rec.confidence >= 0.7
            assert rec.priority in ["high", "medium", "low"]

    def test_recommendation_priority_levels(self):
        """Test recommendation priority assignment."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            analyzer = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            
            # High priority (confidence >= 0.9, frequency >= 5)
            for i in range(6):
                analyzer.record_gap(
                    domain="infrastructure",
                    reason="Test",
                    example=f"test{i}",
                    confidence=0.5
                )
            
            recommendations = analyzer.get_recommendations()
            assert len(recommendations) >= 1
            
            high_rec = recommendations[0]
            assert high_rec.priority == "high"
            assert high_rec.confidence >= 0.9

    def test_generate_expertise_areas(self):
        """Test expertise area generation for different domains."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            analyzer = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            
            # Test infrastructure
            areas = analyzer._generate_expertise_areas("infrastructure")
            assert any("Docker" in area for area in areas)
            assert any("Kubernetes" in area for area in areas)
            
            # Test database
            areas = analyzer._generate_expertise_areas("database")
            assert any("schema" in area for area in areas)
            assert any("Query" in area or "optimization" in area for area in areas)
            
            # Test security
            areas = analyzer._generate_expertise_areas("security")
            assert any("Authentication" in area or "authorization" in area for area in areas)

    def test_generate_agent_markdown(self):
        """Test agent markdown template generation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            analyzer = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            
            recommendation = AgentRecommendation(
                name="infrastructure",
                description="Infrastructure expert",
                domains=["docker", "kubernetes"],
                tools=["*"],
                expertise_areas=["Docker", "Kubernetes", "Terraform"],
                example_scenarios=["Deploy app", "Configure K8s"],
                priority="high",
                confidence=0.85
            )
            
            markdown = analyzer.generate_agent_markdown(recommendation)
            
            # Check YAML frontmatter
            assert markdown.startswith("---")
            assert "name: infrastructure" in markdown
            assert "description: Infrastructure expert" in markdown
            assert "target: github-copilot" in markdown
            
            # Check content
            assert "Infrastructure Agent for EventRelay" in markdown
            assert "Your Expertise" in markdown
            assert "EventRelay Architecture" in markdown
            assert "Code Standards" in markdown
            assert "Example Scenarios" in markdown
            assert "Best Practices" in markdown

    def test_export_recommendation(self):
        """Test exporting recommendation to file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            analyzer = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            
            recommendation = AgentRecommendation(
                name="test-agent",
                description="Test agent",
                domains=["test"],
                tools=["*"],
                expertise_areas=["Testing"],
                example_scenarios=["Test scenario"],
                priority="medium",
                confidence=0.75
            )
            
            output_path = analyzer.export_recommendation(recommendation)
            
            assert output_path.exists()
            assert output_path.name == "test-agent.agent.md"
            
            # Verify content
            content = output_path.read_text()
            assert "name: test-agent" in content
            assert "Testing" in content

    def test_save_and_load_gaps(self):
        """Test saving and loading gaps from storage."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create analyzer and record gaps
            analyzer1 = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            analyzer1.record_gap(
                domain="infrastructure",
                reason="Test",
                example="test.yaml",
                confidence=0.75
            )
            analyzer1.save_gaps()
            
            # Create new analyzer and load gaps
            analyzer2 = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            
            assert "infrastructure" in analyzer2.gaps
            gap = analyzer2.gaps["infrastructure"]
            assert gap.confidence == 0.75
            assert gap.domain == "infrastructure"

    def test_generate_summary_report(self):
        """Test generating summary report."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            analyzer = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            
            # Record some gaps
            for i in range(4):
                analyzer.record_gap(
                    domain="infrastructure",
                    reason="Test",
                    example=f"test{i}",
                    confidence=0.5
                )
            
            report = analyzer.generate_summary_report()
            
            assert "Agent Gap Analysis Report" in report
            assert "Summary" in report
            assert "Detected Gaps" in report
            assert "infrastructure" in report

    def test_edge_case_empty_examples(self):
        """Test handling gaps with no examples."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            analyzer = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            
            gap = AgentGap(
                domain="test",
                confidence=0.8,
                reason="Test reason"
            )
            analyzer.gaps["test"] = gap
            
            # Should not crash when generating report
            report = analyzer.generate_summary_report()
            assert "test" in report

    def test_edge_case_invalid_confidence(self):
        """Test confidence is capped at 1.0."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            analyzer = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            
            # Record many times to max out confidence
            for i in range(20):
                analyzer.record_gap(
                    domain="test",
                    reason="Test",
                    example=f"test{i}",
                    confidence=0.9
                )
            
            gap = analyzer.gaps["test"]
            assert gap.confidence <= 1.0

    def test_multiple_domains_single_context(self):
        """Test detecting multiple domains from single context."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            analyzer = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            
            # Context with multiple domain keywords
            domains = analyzer.detect_domain_from_context(
                "docker-compose.yml with postgresql database and CI/CD pipeline"
            )
            
            assert "infrastructure" in domains
            assert "database" in domains
            assert "devops" in domains


class TestAnalyzerIntegration:
    """Integration tests for the analyzer workflow."""

    def test_full_workflow(self):
        """Test complete workflow from detection to recommendation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            analyzer = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            
            # Step 1: Analyze file access (simulate real usage)
            files = [
                ("infrastructure/k8s/deployment.yaml", "Deploy app"),
                ("infrastructure/k8s/service.yaml", "Configure service"),
                ("infrastructure/helm/values.yaml", "Update chart"),
                ("infrastructure/terraform/main.tf", "Provision infra"),
            ]
            
            for filepath, task in files:
                analyzer.analyze_file_access(filepath, task)
            
            # Step 2: Get recommendations
            recommendations = analyzer.get_recommendations()
            assert len(recommendations) >= 1
            
            # Step 3: Generate agent template
            if recommendations:
                rec = recommendations[0]
                output_path = analyzer.export_recommendation(rec)
                assert output_path.exists()
                
                # Verify template quality
                content = output_path.read_text()
                assert "---" in content  # YAML frontmatter
                assert "name:" in content
                assert "EventRelay" in content

    def test_persistence_across_sessions(self):
        """Test gaps persist across analyzer instances."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Session 1
            analyzer1 = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            analyzer1.analyze_file_access("k8s/deploy.yaml", "Deploy")
            analyzer1.analyze_file_access("k8s/service.yaml", "Service")
            
            # Session 2
            analyzer2 = AgentGapAnalyzer(storage_dir=Path(tmp_dir))
            analyzer2.analyze_file_access("k8s/ingress.yaml", "Ingress")
            
            # Gap should accumulate
            assert "infrastructure" in analyzer2.gaps
            gap = analyzer2.gaps["infrastructure"]
            assert gap.frequency >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
