#!/usr/bin/env python3
"""
Agent Self-Creation Demo
=========================

Demonstrates how the agent gap detection and recommendation system works.

This example shows:
1. Recording gaps from usage patterns
2. Generating recommendations
3. Creating agent templates
4. Complete workflow
"""

import sys
from pathlib import Path

# Import agent_gap_analyzer from the installed package
from youtube_extension.services.agents import agent_gap_analyzer
def demo_basic_workflow():
    """Demonstrate basic workflow of agent gap detection"""
    
    print("=" * 70)
    print("Agent Self-Creation System Demo")
    print("=" * 70)
    print()
    
    # Initialize analyzer
    print("1️⃣  Initializing Agent Gap Analyzer...")
    analyzer = agent_gap_analyzer.AgentGapAnalyzer()
    print("   ✅ Analyzer ready\n")
    
    # Simulate usage patterns
    print("2️⃣  Simulating usage patterns...")
    
    # Infrastructure work
    print("   📁 Working on Kubernetes configuration...")
    analyzer.analyze_file_access(
        "infrastructure/kubernetes/deployment.yaml",
        "Configuring production deployment"
    )
    analyzer.analyze_file_access(
        "infrastructure/kubernetes/service.yaml",
        "Setting up load balancer"
    )
    analyzer.analyze_file_access(
        "infrastructure/helm/values.yaml",
        "Updating Helm chart"
    )
    
    # Database work
    print("   📁 Working on database migrations...")
    analyzer.analyze_file_access(
        "database/migrations/001_create_tables.sql",
        "Creating initial schema"
    )
    analyzer.analyze_file_access(
        "database/migrations/002_add_indexes.sql",
        "Optimizing queries"
    )
    
    # DevOps work
    print("   📁 Working on CI/CD pipeline...")
    analyzer.analyze_file_access(
        ".github/workflows/deploy.yml",
        "Setting up deployment pipeline"
    )
    analyzer.analyze_file_access(
        ".github/workflows/test.yml",
        "Configuring test automation"
    )
    
    # Security work
    print("   📁 Working on authentication...")
    analyzer.analyze_file_access(
        "src/auth/oauth.py",
        "Implementing OAuth2"
    )
    analyzer.analyze_error_pattern(
        "AuthenticationError",
        "JWT token validation failed",
        frequency=3
    )
    
    print("   ✅ Usage patterns recorded\n")
    
    # Check detected gaps
    print("3️⃣  Analyzing detected gaps...")
    print(f"   📊 Total gaps detected: {len(analyzer.gaps)}\n")
    
    for domain, gap in analyzer.gaps.items():
        print(f"   • {domain}")
        print(f"     Confidence: {gap.confidence:.2f}")
        print(f"     Frequency: {gap.frequency}")
        print(f"     Reason: {gap.reason}")
        print()
    
    # Get recommendations
    print("4️⃣  Generating recommendations...")
    recommendations = analyzer.get_recommendations()
    
    if recommendations:
        print(f"   💡 {len(recommendations)} agents recommended:\n")
        
        for i, rec in enumerate(recommendations, 1):
            priority_emoji = {
                "high": "🔴",
                "medium": "🟡",
                "low": "🟢"
            }[rec.priority]
            
            print(f"   {priority_emoji} {i}. {rec.name.upper()}")
            print(f"      Priority: {rec.priority.upper()}")
            print(f"      Confidence: {rec.confidence:.2f}")
            print(f"      Domains: {', '.join(rec.domains[:3])}")
            print()
        
        # Generate template for highest priority
        print("5️⃣  Generating agent template...")
        top_recommendation = recommendations[0]
        output_path = analyzer.export_recommendation(top_recommendation)
        print(f"   ✅ Template created: {output_path}\n")
        
        print("6️⃣  Next steps:")
        print("   1. Review the generated template")
        print("   2. Refine expertise areas and examples")
        print(f"   3. Move to .github/agents/:")
        print(f"      mv {output_path} .github/agents/")
        print("   4. Commit and push to activate")
        print(f"   5. Use with: @{top_recommendation.name} in GitHub Copilot\n")
        
    else:
        print("   ℹ️  No recommendations at this time\n")
    
    # Generate summary report
    print("7️⃣  Generating summary report...")
    report = analyzer.generate_summary_report()
    report_lines = report.split('\n')[:25]  # First 25 lines
    print("   " + "\n   ".join(report_lines))
    print("   ...")
    print()
    
    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print()
    print("To use the real system:")
    print("  python scripts/manage_custom_agents.py analyze --demo")
    print("  python scripts/manage_custom_agents.py recommend")
    print("  python scripts/manage_custom_agents.py generate <agent-name>")
    print()


if __name__ == "__main__":
    demo_basic_workflow()
