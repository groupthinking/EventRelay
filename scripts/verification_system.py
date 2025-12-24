#!/usr/bin/env python3
"""
UVAI Platform Verification System
==================================

Automated verification framework to validate claims against actual implementation.
Identifies gaps between reported status and codebase reality.

USAGE:
    python verification_system.py

OUTPUT:
    Comprehensive verification report with gap analysis
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict

@dataclass
class VerificationResult:
    claim: str
    expected: Any
    actual: Any
    status: str  # 'VERIFIED', 'GAP_FOUND', 'ERROR'
    details: str
    severity: str  # 'CRITICAL', 'MODERATE', 'MINOR'

class UVaiVerificationSystem:
    """Comprehensive verification system for UVAI platform claims"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.results: List[VerificationResult] = []

    def verify_security_hardening(self) -> None:
        """Verify security claims from reports"""

        # Check for exposed .env files
        env_files = list(self.project_root.glob(".env*"))
        exposed_keys = []

        for env_file in env_files:
            if env_file.exists():
                try:
                    with open(env_file, 'r') as f:
                        content = f.read()
                        if any(key in content for key in ['sk-', 'AIzaSy', 'xai-', 'gsk_']):
                            exposed_keys.append(str(env_file))
                except Exception as e:
                    pass

        self.results.append(VerificationResult(
            claim="Credentials secured (moved to environment variables)",
            expected="No hardcoded API keys in .env files",
            actual=f"Found {len(exposed_keys)} files with exposed keys: {exposed_keys}",
            status="GAP_FOUND" if exposed_keys else "VERIFIED",
            details=f"Security violation: {len(exposed_keys)} .env files contain production API keys",
            severity="CRITICAL" if exposed_keys else "MINOR"
        ))

    def verify_mcp_ecosystem(self) -> None:
        """Verify MCP server and tool claims"""

        mcp_dir = self.project_root / "mcp_servers"
        if not mcp_dir.exists():
            self.results.append(VerificationResult(
                claim="8 production MCP servers operational",
                expected="8 MCP server files",
                actual="mcp_servers directory not found",
                status="GAP_FOUND",
                details="MCP servers directory missing",
                severity="MODERATE"
            ))
            return

        server_files = list(mcp_dir.glob("*mcp_server*.py"))
        actual_servers = len(server_files)

        # Count tools across all servers
        total_tools = 0
        server_details = {}

        for server_file in server_files:
            try:
                with open(server_file, 'r') as f:
                    content = f.read()
                    tool_count = content.count('"name"')
                    server_details[server_file.name] = tool_count
                    total_tools += tool_count
            except Exception as e:
                server_details[server_file.name] = 0

        self.results.append(VerificationResult(
            claim="8 production MCP servers with 25+ tools",
            expected="8 servers, 25+ tools",
            actual=f"{actual_servers} servers, {total_tools} tools",
            status="GAP_FOUND" if actual_servers < 8 or total_tools < 25 else "VERIFIED",
            details=f"Server breakdown: {server_details}",
            severity="MODERATE"
        ))

    def verify_backend_architecture(self) -> None:
        """Verify backend service-oriented architecture claims"""

        main_v2 = self.project_root / "backend" / "main_v2.py"
        services_dir = self.project_root / "backend" / "services"

        if not main_v2.exists():
            self.results.append(VerificationResult(
                claim="Service-oriented architecture with main_v2.py",
                expected="main_v2.py exists",
                actual="main_v2.py not found",
                status="GAP_FOUND",
                details="Production entry point missing",
                severity="CRITICAL"
            ))
            return

        if not services_dir.exists():
            self.results.append(VerificationResult(
                claim="8 dedicated service classes",
                expected="services directory with 8+ service files",
                actual="services directory not found",
                status="GAP_FOUND",
                details="Service layer missing",
                severity="CRITICAL"
            ))
            return

        service_files = list(services_dir.glob("*service*.py"))
        actual_services = len(service_files)

        self.results.append(VerificationResult(
            claim="8 dedicated service classes",
            expected="8+ service files",
            actual=f"{actual_services} service files",
            status="VERIFIED" if actual_services >= 8 else "GAP_FOUND",
            details=f"Found services: {[f.name for f in service_files[:5]]}{'...' if len(service_files) > 5 else ''}",
            severity="MINOR" if actual_services >= 8 else "MODERATE"
        ))

    def verify_frontend_migrations(self) -> None:
        """Verify frontend component migration claims"""

        components_dir = self.project_root / "frontend" / "src" / "components"

        key_components = [
            "RealLearningAgent.tsx",
            "EnhancedLearningHub.tsx",
            "ComponentMigrationIndex.ts"
        ]

        missing_components = []
        found_components = []

        for component in key_components:
            if (components_dir / component).exists():
                found_components.append(component)
            else:
                missing_components.append(component)

        self.results.append(VerificationResult(
            claim="Superior React components migrated to production",
            expected=f"All components: {key_components}",
            actual=f"Found: {found_components}, Missing: {missing_components}",
            status="VERIFIED" if not missing_components else "GAP_FOUND",
            details=f"Migration status: {len(found_components)}/{len(key_components)} components verified",
            severity="MINOR"
        ))

    def verify_performance_claims(self) -> None:
        """Verify performance benchmark claims"""

        benchmark_file = self.project_root / "backend" / "services" / "performance_benchmark_system.py"

        if not benchmark_file.exists():
            self.results.append(VerificationResult(
                claim="60%+ performance improvements validated",
                expected="Performance benchmark system exists",
                actual="performance_benchmark_system.py not found",
                status="GAP_FOUND",
                details="Performance validation system missing",
                severity="MODERATE"
            ))
            return

        # Test if benchmark system can be imported
        try:
            import sys
            # REMOVED: sys.path.append removed
            import performance_benchmark_system
            import_status = "Import successful"
            severity = "MINOR"
        except Exception as e:
            import_status = f"Import failed: {str(e)[:100]}"
            severity = "MODERATE"

        self.results.append(VerificationResult(
            claim="60%+ performance improvements with benchmark validation",
            expected="Working performance benchmark system",
            actual=import_status,
            status="GAP_FOUND" if "failed" in import_status.lower() else "VERIFIED",
            details="Performance claims require validation testing",
            severity=severity
        ))

    def verify_database_integration(self) -> None:
        """Verify Thenile database integration claims"""

        db_config = self.project_root / "backend" / "config" / "database.py"

        if not db_config.exists():
            self.results.append(VerificationResult(
                claim="Thenile PostgreSQL integration",
                expected="database.py configuration file",
                actual="Database config not found",
                status="GAP_FOUND",
                details="Database integration configuration missing",
                severity="MODERATE"
            ))
            return

        try:
            with open(db_config, 'r') as f:
                content = f.read()
                if "thenile" in content.lower() or "postgresql" in content:
                    status = "VERIFIED"
                    details = "Thenile PostgreSQL configuration found"
                else:
                    status = "GAP_FOUND"
                    details = "Database config exists but Thenile integration unclear"
        except Exception as e:
            status = "ERROR"
            details = f"Error reading database config: {e}"

        self.results.append(VerificationResult(
            claim="Thenile PostgreSQL multi-tenant database",
            expected="Thenile database configuration",
            actual=details,
            status=status,
            details="Database integration verification",
            severity="MINOR"
        ))

    def run_full_verification(self) -> Dict[str, Any]:
        """Run complete verification suite"""

        print("🔍 Starting UVAI Platform Verification...")
        print("=" * 50)

        # Run all verification checks
        self.verify_security_hardening()
        self.verify_mcp_ecosystem()
        self.verify_backend_architecture()
        self.verify_frontend_migrations()
        self.verify_performance_claims()
        self.verify_database_integration()

        # Generate report
        report = self.generate_report()
        self.save_report(report)

        return report

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive verification report"""

        verified = len([r for r in self.results if r.status == "VERIFIED"])
        gaps_found = len([r for r in self.results if r.status == "GAP_FOUND"])
        errors = len([r for r in self.results if r.status == "ERROR"])
        critical_gaps = len([r for r in self.results if r.severity == "CRITICAL"])

        return {
            "summary": {
                "total_checks": len(self.results),
                "verified": verified,
                "gaps_found": gaps_found,
                "errors": errors,
                "critical_gaps": critical_gaps,
                "verification_rate": f"{verified}/{len(self.results)} ({verified/len(self.results)*100:.1f}%)"
            },
            "results": [asdict(result) for result in self.results],
            "recommendations": self.generate_recommendations()
        }

    def generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on findings"""

        recommendations = []

        critical_results = [r for r in self.results if r.severity == "CRITICAL"]
        if critical_results:
            recommendations.append("🚨 CRITICAL: Address security violations immediately")
            recommendations.append("🚨 CRITICAL: Fix exposed production API keys")

        gap_results = [r for r in self.results if r.status == "GAP_FOUND"]
        if gap_results:
            recommendations.append("🔧 MODERATE: Update reports to reflect actual implementation status")
            recommendations.append("🔧 MODERATE: Align claims with verified capabilities")

        recommendations.extend([
            "📊 Create automated verification system for ongoing validation",
            "📊 Implement CI/CD verification gates",
            "📊 Establish regular gap analysis process"
        ])

        return recommendations

    def save_report(self, report: Dict[str, Any]) -> None:
        """Save verification report to file"""

        report_file = self.project_root / "VERIFICATION_REPORT.json"

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"📄 Verification report saved to: {report_file}")

    def print_report(self, report: Dict[str, Any]) -> None:
        """Print human-readable verification report"""

        print("\n" + "="*60)
        print("🎯 UVAI PLATFORM VERIFICATION REPORT")
        print("="*60)

        summary = report["summary"]
        print(f"\n📊 SUMMARY:")
        print(f"   Total Checks: {summary['total_checks']}")
        print(f"   ✅ Verified: {summary['verified']}")
        print(f"   ❌ Gaps Found: {summary['gaps_found']}")
        print(f"   ⚠️  Errors: {summary['errors']}")
        print(f"   🚨 Critical Gaps: {summary['critical_gaps']}")
        print(f"   📈 Verification Rate: {summary['verification_rate']}")

        print(f"\n🔍 DETAILED RESULTS:")
        for result in report["results"]:
            status_icon = {
                "VERIFIED": "✅",
                "GAP_FOUND": "❌",
                "ERROR": "⚠️"
            }.get(result["status"], "?")

            severity_icon = {
                "CRITICAL": "🚨",
                "MODERATE": "🟡",
                "MINOR": "🔵"
            }.get(result["severity"], "?")

            print(f"\n{status_icon} {severity_icon} {result['claim']}")
            print(f"   Expected: {result['expected']}")
            print(f"   Actual: {result['actual']}")
            print(f"   Details: {result['details']}")

        print(f"\n💡 RECOMMENDATIONS:")
        for rec in report["recommendations"]:
            print(f"   • {rec}")

        print("\n" + "="*60)

def main():
    """Main entry point for verification system"""

    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir

    # Initialize verification system
    verifier = UVaiVerificationSystem(str(project_root))

    # Run verification
    report = verifier.run_full_verification()

    # Print report
    verifier.print_report(report)

    # Exit with appropriate code
    critical_gaps = report["summary"]["critical_gaps"]
    sys.exit(0 if critical_gaps == 0 else 1)

if __name__ == "__main__":
    main()
