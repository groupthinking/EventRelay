#!/usr/bin/env python3
"""
Agent Gap Analyzer
==================

Analyzes issues, tasks, and system performance to identify gaps in custom
GitHub Copilot agent coverage and recommend new agent creation.

This system detects when:
- Issues require specialized expertise not covered by existing agents
- Performance could be enhanced with domain-specific guidance
- Patterns emerge that warrant dedicated agent support
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
import json


@dataclass
class AgentGap:
    """Represents a detected gap in agent coverage"""
    domain: str
    confidence: float  # 0.0 to 1.0
    reason: str
    examples: List[str] = field(default_factory=list)
    frequency: int = 1
    first_detected: datetime = field(default_factory=datetime.now)
    last_detected: datetime = field(default_factory=datetime.now)


@dataclass
class AgentRecommendation:
    """Recommendation for creating a new custom agent"""
    name: str
    description: str
    domains: List[str]
    tools: List[str]
    expertise_areas: List[str]
    example_scenarios: List[str]
    priority: str  # "high", "medium", "low"
    confidence: float
    supporting_gaps: List[AgentGap] = field(default_factory=list)


class AgentGapAnalyzer:
    """
    Analyzes system usage to identify when new custom agents should be created.
    
    This analyzer tracks:
    - File types and technologies frequently edited without agent support
    - Repeated error patterns that could benefit from specialized guidance
    - Domain-specific tasks that lack dedicated agent coverage
    - Performance issues that specialized agents could address
    """
    
    # Existing agent domains (from current .github/agents/*.agent.md files)
    EXISTING_AGENTS = {
        "python-backend": ["python", "fastapi", "backend", "api", "asyncio", "sqlalchemy"],
        "frontend": ["react", "typescript", "frontend", "hooks", "jsx", "tsx"],
        "testing": ["pytest", "jest", "testing", "coverage", "fixtures"],
        "mcp": ["mcp", "json-rpc", "protocol", "agent-orchestration"],
        "documentation": ["markdown", "docs", "api-docs", "technical-writing"],
        "video-processing": ["video", "youtube", "transcription", "ai-analysis", "rag"],
    }
    
    # Technology/domain keywords to monitor
    TECHNOLOGY_KEYWORDS = {
        "infrastructure": ["docker", "kubernetes", "k8s", "helm", "terraform", "ansible"],
        "database": ["postgresql", "mongodb", "redis", "sql", "database", "migration"],
        "security": ["auth", "oauth", "jwt", "encryption", "security", "vulnerability"],
        "devops": ["ci", "cd", "github-actions", "deployment", "pipeline"],
        "performance": ["optimization", "profiling", "caching", "scalability"],
        "data-science": ["pandas", "numpy", "scikit-learn", "data-analysis", "ml"],
        "mobile": ["ios", "android", "react-native", "flutter", "mobile"],
        "blockchain": ["web3", "ethereum", "solidity", "smart-contract"],
        "ai-ml": ["machine-learning", "neural-network", "tensorflow", "pytorch", "llm"],
    }
    
    # Minimum confidence threshold for recommendations
    RECOMMENDATION_THRESHOLD = 0.7
    
    # Minimum frequency before recommending new agent
    MIN_FREQUENCY = 3

    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize agent gap analyzer.
        
        Args:
            storage_dir: Directory to store gap analysis data
        """
        self.logger = logging.getLogger("agent_gap_analyzer")
        self.storage_dir = storage_dir or Path.home() / ".eventrelay" / "agent_gaps"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.gaps: Dict[str, AgentGap] = {}
        self.load_gaps()

    def load_gaps(self) -> None:
        """Load previously detected gaps from storage"""
        gaps_file = self.storage_dir / "gaps.json"
        if gaps_file.exists():
            try:
                with open(gaps_file, 'r') as f:
                    data = json.load(f)
                    for domain, gap_data in data.items():
                        self.gaps[domain] = AgentGap(
                            domain=gap_data["domain"],
                            confidence=gap_data["confidence"],
                            reason=gap_data["reason"],
                            examples=gap_data.get("examples", []),
                            frequency=gap_data.get("frequency", 1),
                            first_detected=datetime.fromisoformat(gap_data["first_detected"]),
                            last_detected=datetime.fromisoformat(gap_data["last_detected"])
                        )
                self.logger.info(f"Loaded {len(self.gaps)} existing gaps")
            except Exception as e:
                self.logger.error(f"Failed to load gaps: {e}")

    def save_gaps(self) -> None:
        """Save detected gaps to storage"""
        gaps_file = self.storage_dir / "gaps.json"
        try:
            data = {
                domain: {
                    "domain": gap.domain,
                    "confidence": gap.confidence,
                    "reason": gap.reason,
                    "examples": gap.examples[-10:],  # Keep last 10 examples
                    "frequency": gap.frequency,
                    "first_detected": gap.first_detected.isoformat(),
                    "last_detected": gap.last_detected.isoformat()
                }
                for domain, gap in self.gaps.items()
            }
            with open(gaps_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.debug(f"Saved {len(self.gaps)} gaps")
        except Exception as e:
            self.logger.error(f"Failed to save gaps: {e}")

    def detect_domain_from_context(self, context: str) -> Set[str]:
        """
        Detect technology domains from context (file path, content, etc.)
        
        Args:
            context: Context string to analyze (file path, code snippet, etc.)
            
        Returns:
            Set of detected domain keywords
        """
        context_lower = context.lower()
        detected = set()
        
        for domain, keywords in self.TECHNOLOGY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in context_lower:
                    detected.add(domain)
                    break
        
        return detected

    def is_domain_covered(self, domain: str) -> bool:
        """
        Check if a domain is adequately covered by existing agents.
        
        Args:
            domain: Domain to check
            
        Returns:
            True if domain is covered by existing agents
        """
        for agent_domains in self.EXISTING_AGENTS.values():
            if domain in agent_domains or any(d in domain for d in agent_domains):
                return True
        return False

    def record_gap(self, domain: str, reason: str, example: str, confidence: float = 0.5) -> None:
        """
        Record a detected gap in agent coverage.
        
        Args:
            domain: Technology domain with insufficient coverage
            reason: Explanation of why this gap exists
            example: Example scenario demonstrating the gap
            confidence: Confidence level (0.0 to 1.0)
        """
        if domain in self.gaps:
            gap = self.gaps[domain]
            gap.frequency += 1
            gap.last_detected = datetime.now()
            gap.confidence = min(1.0, gap.confidence + 0.1)  # Increase confidence
            if example not in gap.examples:
                gap.examples.append(example)
        else:
            self.gaps[domain] = AgentGap(
                domain=domain,
                confidence=confidence,
                reason=reason,
                examples=[example]
            )
        
        self.save_gaps()
        self.logger.info(f"Recorded gap for domain '{domain}' (frequency: {self.gaps[domain].frequency})")

    def analyze_file_access(self, file_path: str, task_description: str = "") -> None:
        """
        Analyze file access to detect potential gaps in agent coverage.
        
        Args:
            file_path: Path of file being accessed
            task_description: Description of task being performed
        """
        domains = self.detect_domain_from_context(file_path + " " + task_description)
        
        for domain in domains:
            if not self.is_domain_covered(domain):
                reason = f"Frequent work in {domain} without dedicated agent support"
                example = f"Working on: {file_path}"
                if task_description:
                    example += f" - {task_description}"
                self.record_gap(domain, reason, example, confidence=0.6)

    def analyze_error_pattern(self, error_type: str, context: str, frequency: int = 1) -> None:
        """
        Analyze error patterns to identify gaps that specialized agents could address.
        
        Args:
            error_type: Type/category of error
            context: Context where error occurred
            frequency: How many times this error has occurred
        """
        domains = self.detect_domain_from_context(error_type + " " + context)
        
        for domain in domains:
            if not self.is_domain_covered(domain) and frequency >= 2:
                reason = f"Repeated {error_type} errors in {domain} domain"
                example = f"Error context: {context}"
                confidence = min(0.9, 0.5 + (frequency * 0.1))
                self.record_gap(domain, reason, example, confidence=confidence)

    def get_recommendations(self) -> List[AgentRecommendation]:
        """
        Generate recommendations for new agents based on detected gaps.
        
        Returns:
            List of agent recommendations, sorted by priority
        """
        recommendations = []
        
        for domain, gap in self.gaps.items():
            # Only recommend if gap meets thresholds
            if gap.confidence < self.RECOMMENDATION_THRESHOLD:
                continue
            if gap.frequency < self.MIN_FREQUENCY:
                continue
            
            # Generate agent recommendation
            agent_name = domain.replace("_", "-")
            
            # Determine priority based on confidence and frequency
            if gap.confidence >= 0.9 and gap.frequency >= 5:
                priority = "high"
            elif gap.confidence >= 0.8 and gap.frequency >= 4:
                priority = "medium"
            else:
                priority = "low"
            
            # Get specific keywords for this domain
            domains_list = self.TECHNOLOGY_KEYWORDS.get(domain, [domain])
            
            recommendation = AgentRecommendation(
                name=agent_name,
                description=f"Expert guidance for {domain} development in EventRelay",
                domains=domains_list,
                tools=["*"],  # All tools by default
                expertise_areas=self._generate_expertise_areas(domain),
                example_scenarios=gap.examples[:5],  # Top 5 examples
                priority=priority,
                confidence=gap.confidence,
                supporting_gaps=[gap]
            )
            
            recommendations.append(recommendation)
        
        # Sort by priority and confidence
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(
            key=lambda r: (priority_order[r.priority], -r.confidence)
        )
        
        return recommendations

    def _generate_expertise_areas(self, domain: str) -> List[str]:
        """Generate expertise areas for a given domain"""
        base_areas = [
            f"{domain.replace('-', ' ').title()} best practices",
            "EventRelay integration patterns",
            "Error handling and debugging",
            "Performance optimization",
            "Testing strategies"
        ]
        
        # Add domain-specific areas
        if domain == "infrastructure":
            base_areas.extend([
                "Docker containerization",
                "Kubernetes orchestration",
                "Infrastructure as Code"
            ])
        elif domain == "database":
            base_areas.extend([
                "Database schema design",
                "Query optimization",
                "Migration management"
            ])
        elif domain == "security":
            base_areas.extend([
                "Authentication and authorization",
                "Security vulnerability prevention",
                "Secure coding practices"
            ])
        elif domain == "devops":
            base_areas.extend([
                "CI/CD pipeline configuration",
                "Deployment automation",
                "GitHub Actions workflows"
            ])
        
        return base_areas

    def generate_agent_markdown(self, recommendation: AgentRecommendation) -> str:
        """
        Generate markdown content for a new agent based on recommendation.
        
        Args:
            recommendation: Agent recommendation to generate from
            
        Returns:
            Markdown content for .agent.md file
        """
        # Generate YAML frontmatter
        frontmatter = f"""---
name: {recommendation.name}
description: {recommendation.description}
tools: {json.dumps(recommendation.tools)}
target: github-copilot
metadata:
  maintainer: eventrelay-team
  version: 1.0.0
  domains: {json.dumps(recommendation.domains)}
  auto_generated: true
  confidence: {recommendation.confidence:.2f}
  priority: {recommendation.priority}
---
"""
        
        # Generate agent content
        content = f"""
# {recommendation.name.replace('-', ' ').title()} Agent for EventRelay

You are a senior {recommendation.domains[0]} engineer specializing in the EventRelay project.

## Your Expertise

{'\n'.join(f'- **{area}**' for area in recommendation.expertise_areas)}

## Project Context

### EventRelay Architecture
EventRelay follows a single workflow:
1. **Paste YouTube Link** → User provides URL
2. **Extract Context** → Transcribe video, extract events
3. **Spawn Agents** → Dispatch based on events
4. **Run Tasks** → Execute real-world actions
5. **Publish Outputs** → Deliver results

### Your Role
You provide expert guidance for {recommendation.domains[0]}-related tasks within this workflow.

## Code Standards

### Type Safety
- Use appropriate type hints/annotations
- Validate inputs and outputs
- Handle edge cases gracefully

### Error Handling
- Comprehensive try-catch blocks
- Proper logging with context
- Graceful degradation

### Testing
- >80% code coverage target
- Use standard test video ID: `auJzb1D-fag`
- Real filesystem operations (no mocks)

## Example Scenarios

This agent was created to address the following recurring needs:

{'\n'.join(f'{i+1}. {example}' for i, example in enumerate(recommendation.example_scenarios))}

## Best Practices

1. **Follow EventRelay Conventions**: Maintain consistency with existing codebase
2. **Security First**: Never hardcode secrets, validate all inputs
3. **Performance Aware**: Consider scalability and optimization
4. **Document Thoroughly**: Clear comments and docstrings
5. **Test Comprehensively**: Write tests alongside code

## Boundaries

### What You Should Do
- Provide {recommendation.domains[0]}-specific guidance
- Suggest best practices for EventRelay integration
- Help debug {recommendation.domains[0]}-related issues
- Recommend appropriate tools and libraries

### What You Should Avoid
- Modifying core workflow logic without justification
- Suggesting patterns inconsistent with EventRelay architecture
- Breaking existing functionality
- Introducing unnecessary dependencies

## Integration with Other Agents

You work alongside:
- **@python-backend**: For backend API integration
- **@frontend**: For UI/UX considerations
- **@testing**: For test strategy and coverage
- **@mcp**: For agent orchestration
- **@documentation**: For comprehensive docs
- **@video-processing**: For video workflow integration

When tasks span multiple domains, collaborate by deferring to the appropriate agent.

## Resources

- EventRelay Docs: `/docs/CLAUDE.md`
- Copilot Instructions: `/.github/copilot-instructions.md`
- Existing Agents: `/.github/agents/`

---

**Note**: This agent was automatically generated based on detected patterns in repository usage.
Review and refine as needed for optimal performance.
"""
        
        return frontmatter + content

    def export_recommendation(self, recommendation: AgentRecommendation, output_dir: Optional[Path] = None) -> Path:
        """
        Export agent recommendation to a markdown file for review.
        
        Args:
            recommendation: Recommendation to export
            output_dir: Directory to export to (defaults to storage_dir/recommendations)
            
        Returns:
            Path to exported file
        """
        if output_dir is None:
            output_dir = self.storage_dir / "recommendations"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{recommendation.name}.agent.md"
        filepath = output_dir / filename
        
        content = self.generate_agent_markdown(recommendation)
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        self.logger.info(f"Exported agent recommendation to {filepath}")
        return filepath

    def generate_summary_report(self) -> str:
        """
        Generate a summary report of detected gaps and recommendations.
        
        Returns:
            Markdown report
        """
        recommendations = self.get_recommendations()
        
        report = f"""# Agent Gap Analysis Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

- **Total Gaps Detected**: {len(self.gaps)}
- **High Priority Recommendations**: {sum(1 for r in recommendations if r.priority == 'high')}
- **Medium Priority Recommendations**: {sum(1 for r in recommendations if r.priority == 'medium')}
- **Low Priority Recommendations**: {sum(1 for r in recommendations if r.priority == 'low')}

## Detected Gaps

| Domain | Confidence | Frequency | Status |
|--------|-----------|-----------|--------|
"""
        
        for domain, gap in sorted(self.gaps.items(), key=lambda x: x[1].confidence, reverse=True):
            status = "✅ Recommended" if gap.confidence >= self.RECOMMENDATION_THRESHOLD and gap.frequency >= self.MIN_FREQUENCY else "⏳ Monitoring"
            report += f"| {domain} | {gap.confidence:.2f} | {gap.frequency} | {status} |\n"
        
        if recommendations:
            report += f"\n## Recommended New Agents\n\n"
            for i, rec in enumerate(recommendations, 1):
                report += f"""
### {i}. {rec.name.title()} Agent

**Priority**: {rec.priority.upper()}  
**Confidence**: {rec.confidence:.2f}  
**Domains**: {', '.join(rec.domains)}

**Description**: {rec.description}

**Example Scenarios**:
{'\n'.join(f'- {example}' for example in rec.example_scenarios[:3])}

**Action**: Review generated agent at `.eventrelay/agent_gaps/recommendations/{rec.name}.agent.md`

---
"""
        else:
            report += "\n## No New Agents Recommended\n\nAll detected gaps are either covered by existing agents or below recommendation thresholds.\n"
        
        return report


# Convenience function for easy import
def analyze_agent_gaps() -> AgentGapAnalyzer:
    """Create and return an AgentGapAnalyzer instance"""
    return AgentGapAnalyzer()
