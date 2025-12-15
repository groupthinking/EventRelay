#!/usr/bin/env python3
"""
Custom Agent Management CLI
============================

Command-line tool for managing GitHub Copilot custom agents in EventRelay.

Features:
- Analyze gaps in agent coverage
- Generate recommendations for new agents
- Create agent templates from recommendations
- Review and approve new agents
- Monitor agent usage and effectiveness

Usage:
    python scripts/manage_custom_agents.py analyze
    python scripts/manage_custom_agents.py recommend
    python scripts/manage_custom_agents.py generate <agent-name>
    python scripts/manage_custom_agents.py report
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Add src to path - import the module file directly to avoid package dependencies
agent_gap_module_path = Path(__file__).parent.parent / "src" / "youtube_extension" / "services" / "agents"
sys.path.insert(0, str(agent_gap_module_path))

import agent_gap_analyzer
AgentGapAnalyzer = agent_gap_analyzer.AgentGapAnalyzer
AgentRecommendation = agent_gap_analyzer.AgentRecommendation


def cmd_analyze(args) -> int:
    """Analyze current agent coverage and detect gaps"""
    analyzer = AgentGapAnalyzer()
    
    # Simulate some gap detection (in real use, this would come from monitoring)
    if args.demo:
        print("🔍 Running demo analysis with sample data...\n")
        analyzer.analyze_file_access(
            "infrastructure/kubernetes/deployment.yaml",
            "Configuring production deployment"
        )
        analyzer.analyze_file_access(
            "infrastructure/docker/Dockerfile.production",
            "Optimizing container build"
        )
        analyzer.analyze_file_access(
            "database/migrations/001_add_user_table.sql",
            "Creating database migration"
        )
        analyzer.analyze_error_pattern(
            "DatabaseConnectionError",
            "PostgreSQL connection timeout in production",
            frequency=4
        )
        analyzer.analyze_file_access(
            ".github/workflows/deploy.yml",
            "Setting up CI/CD pipeline"
        )
        print("✅ Demo analysis complete!\n")
    
    # Display current gaps
    if analyzer.gaps:
        print("📊 Detected Gaps in Agent Coverage:\n")
        print(f"{'Domain':<20} {'Confidence':<12} {'Frequency':<12} {'Status'}")
        print("-" * 70)
        
        for domain, gap in sorted(
            analyzer.gaps.items(),
            key=lambda x: (x[1].confidence, x[1].frequency),
            reverse=True
        ):
            status = "🔴 Critical" if gap.frequency >= 5 else "🟡 Monitoring"
            print(f"{domain:<20} {gap.confidence:>6.2f}      {gap.frequency:>6}        {status}")
        
        print(f"\n📈 Total gaps detected: {len(analyzer.gaps)}")
        return 0
    else:
        print("✅ No gaps detected - all domains are adequately covered!")
        return 0


def cmd_recommend(args) -> int:
    """Generate recommendations for new agents"""
    analyzer = AgentGapAnalyzer()
    recommendations = analyzer.get_recommendations()
    
    if not recommendations:
        print("ℹ️  No new agents recommended at this time.")
        print("   Current gaps don't meet recommendation thresholds.")
        return 0
    
    print(f"💡 Agent Recommendations ({len(recommendations)} total):\n")
    
    for i, rec in enumerate(recommendations, 1):
        priority_emoji = {
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢"
        }[rec.priority]
        
        print(f"{priority_emoji} {i}. {rec.name.upper()} Agent")
        print(f"   Priority: {rec.priority.upper()}")
        print(f"   Confidence: {rec.confidence:.2f}")
        print(f"   Domains: {', '.join(rec.domains)}")
        print(f"   Description: {rec.description}")
        print()
    
    print(f"💾 To generate agent files, run:")
    print(f"   python scripts/manage_custom_agents.py generate <agent-name>")
    
    return 0


def cmd_generate(args) -> int:
    """Generate agent markdown file from recommendation"""
    analyzer = AgentGapAnalyzer()
    recommendations = analyzer.get_recommendations()
    
    # Find matching recommendation
    matching_rec = None
    for rec in recommendations:
        if rec.name == args.agent_name:
            matching_rec = rec
            break
    
    if not matching_rec:
        print(f"❌ No recommendation found for agent: {args.agent_name}")
        print(f"\nAvailable recommendations:")
        for rec in recommendations:
            print(f"  - {rec.name}")
        return 1
    
    # Export to recommendations directory
    output_path = analyzer.export_recommendation(matching_rec)
    
    print(f"✅ Generated agent file: {output_path}")
    print(f"\n📋 Next steps:")
    print(f"   1. Review the generated file")
    print(f"   2. Refine expertise areas and examples")
    print(f"   3. Move to .github/agents/ directory:")
    print(f"      mv {output_path} .github/agents/")
    print(f"   4. Commit and push to activate the agent")
    print(f"\n💡 Invoke with: @{matching_rec.name} in GitHub Copilot Chat")
    
    return 0


def cmd_report(args) -> int:
    """Generate comprehensive gap analysis report"""
    analyzer = AgentGapAnalyzer()
    report = analyzer.generate_summary_report()
    
    # Save report
    report_dir = analyzer.storage_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = report_dir / f"gap_analysis_{timestamp}.md"
    
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(report)
    print(f"\n💾 Report saved to: {report_path}")
    
    return 0


def cmd_list(args) -> int:
    """List all existing custom agents"""
    agents_dir = Path(".github/agents")
    
    if not agents_dir.exists():
        print("❌ .github/agents directory not found")
        return 1
    
    agent_files = list(agents_dir.glob("*.agent.md"))
    
    if not agent_files:
        print("ℹ️  No custom agents found")
        return 0
    
    print(f"📚 Existing Custom Agents ({len(agent_files)}):\n")
    
    for agent_file in sorted(agent_files):
        # Parse YAML frontmatter to get name and description
        with open(agent_file, 'r') as f:
            content = f.read()
            if content.startswith("---"):
                frontmatter = content.split("---")[1]
                name = None
                description = None
                for line in frontmatter.split("\n"):
                    if line.startswith("name:"):
                        name = line.split(":", 1)[1].strip()
                    elif line.startswith("description:"):
                        description = line.split(":", 1)[1].strip()
                
                if name and description:
                    print(f"✅ @{name}")
                    print(f"   {description}")
                    print(f"   File: {agent_file.name}")
                    print()
    
    return 0


def cmd_validate(args) -> int:
    """Validate existing agent files"""
    agents_dir = Path(".github/agents")
    
    if not agents_dir.exists():
        print("❌ .github/agents directory not found")
        return 1
    
    agent_files = list(agents_dir.glob("*.agent.md"))
    
    if not agent_files:
        print("ℹ️  No custom agents found")
        return 0
    
    print(f"🔍 Validating {len(agent_files)} agent files...\n")
    
    all_valid = True
    required_fields = ["name", "description", "tools", "target"]
    
    for agent_file in sorted(agent_files):
        print(f"Checking {agent_file.name}...", end=" ")
        
        with open(agent_file, 'r') as f:
            content = f.read()
        
        # Check for YAML frontmatter
        if not content.startswith("---"):
            print("❌ Missing YAML frontmatter")
            all_valid = False
            continue
        
        # Extract frontmatter
        parts = content.split("---")
        if len(parts) < 3:
            print("❌ Invalid YAML frontmatter structure")
            all_valid = False
            continue
        
        frontmatter = parts[1]
        
        # Check required fields
        missing_fields = []
        for field in required_fields:
            if f"{field}:" not in frontmatter:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ Missing fields: {', '.join(missing_fields)}")
            all_valid = False
            continue
        
        print("✅")
    
    if all_valid:
        print("\n✅ All agent files are valid!")
        return 0
    else:
        print("\n❌ Some agent files have validation errors")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Manage GitHub Copilot custom agents for EventRelay",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze current agent coverage
  python scripts/manage_custom_agents.py analyze --demo
  
  # Get recommendations for new agents
  python scripts/manage_custom_agents.py recommend
  
  # Generate a specific agent
  python scripts/manage_custom_agents.py generate infrastructure
  
  # Generate full report
  python scripts/manage_custom_agents.py report
  
  # List existing agents
  python scripts/manage_custom_agents.py list
  
  # Validate agent files
  python scripts/manage_custom_agents.py validate
"""
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze agent coverage and detect gaps"
    )
    analyze_parser.add_argument(
        "--demo",
        action="store_true",
        help="Run with demo data"
    )
    
    # Recommend command
    subparsers.add_parser(
        "recommend",
        help="Generate recommendations for new agents"
    )
    
    # Generate command
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate agent markdown file"
    )
    generate_parser.add_argument(
        "agent_name",
        help="Name of agent to generate (e.g., 'infrastructure')"
    )
    
    # Report command
    subparsers.add_parser(
        "report",
        help="Generate comprehensive gap analysis report"
    )
    
    # List command
    subparsers.add_parser(
        "list",
        help="List all existing custom agents"
    )
    
    # Validate command
    subparsers.add_parser(
        "validate",
        help="Validate existing agent files"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    commands = {
        "analyze": cmd_analyze,
        "recommend": cmd_recommend,
        "generate": cmd_generate,
        "report": cmd_report,
        "list": cmd_list,
        "validate": cmd_validate
    }
    
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
