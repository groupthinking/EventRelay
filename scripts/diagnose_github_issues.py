#!/usr/bin/env python3
"""
GitHub Processing Issues Diagnostic Script

Comprehensive diagnostic tool to identify root causes of GitHub processing bottlenecks and lock-ups.
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [DIAGNOSTIC] %(message)s'
)
logger = logging.getLogger(__name__)

class GitHubDiagnostic:
    def __init__(self):
        self.project_root = Path(".")
        self.issues_found = []
        self.recommendations = []

    def check_timeout_conflicts(self) -> bool:
        """Check for conflicting timeout configurations"""
        logger.info("🔍 Checking for timeout configuration conflicts...")

        # Check main config file
        config_path = self.project_root / "config" / "llama_agent_config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)

                processing_timeout = config.get("llama_agent", {}).get("processing", {}).get("timeout", 0)
                resource_timeout = config.get("llama_agent", {}).get("performance", {}).get("resource_limits", {}).get("max_processing_time", 0)

                if processing_timeout != resource_timeout and processing_timeout != 0 and resource_timeout != 0:
                    self.issues_found.append(f"⚠️  Timeout conflict: processing={processing_timeout}s, resource_limit={resource_timeout}s")
                    self.recommendations.append("Fix timeout configuration inconsistency")
                    return False
                elif processing_timeout > 600 or resource_timeout > 600:
                    self.issues_found.append(f"⚠️  High timeout values: processing={processing_timeout}s, resource_limit={resource_timeout}s")
                    self.recommendations.append("Reduce timeout values to under 600 seconds for better performance")
                    return False
                else:
                    logger.info(f"✅ Timeout configuration: {processing_timeout}s")
                    return True
            except Exception as e:
                self.issues_found.append(f"❌ Failed to read config: {e}")
                return False

        self.issues_found.append("❌ Config file not found")
        return False

    def check_workflow_configurations(self) -> bool:
        """Check GitHub workflow configurations for issues"""
        logger.info("🔍 Checking GitHub workflow configurations...")

        workflow_dir = self.project_root / ".github" / "workflows"
        if not workflow_dir.exists():
            self.issues_found.append("❌ .github/workflows directory not found")
            return False

        workflow_files = list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml"))
        issues = 0

        for wf_file in workflow_files:
            try:
                with open(wf_file, 'r') as f:
                    content = f.read()

                # Check for potential issues
                if "timeout-minutes: 0" in content or "timeout-minutes: null" in content:
                    self.issues_found.append(f"⚠️  Invalid timeout in {wf_file.name}")
                    issues += 1

                if "runs-on: ubuntu-latest" in content and "timeout-minutes:" not in content:
                    self.issues_found.append(f"⚠️  No timeout set in {wf_file.name}")
                    issues += 1

                if "concurrency:" not in content and "workflow_dispatch" in content:
                    self.issues_found.append(f"⚠️  No concurrency control in {wf_file.name}")
                    issues += 1

            except Exception as e:
                self.issues_found.append(f"❌ Failed to read {wf_file.name}: {e}")
                issues += 1

        if issues == 0:
            logger.info(f"✅ Checked {len(workflow_files)} workflow files")
            return True
        else:
            self.recommendations.append("Fix workflow configuration issues")
            return False

    def check_environment_variables(self) -> bool:
        """Check environment variable configurations"""
        logger.info("🔍 Checking environment configurations...")

        env_files = list(self.project_root.glob(".env*"))
        mcp_env_found = False

        for env_file in env_files:
            if env_file.name == ".env.mcp":
                mcp_env_found = True
                try:
                    with open(env_file, 'r') as f:
                        content = f.read()

                    # Check for required MCP variables
                    required_vars = ["MCP_TIMEOUT", "MCP_MAX_CONCURRENT", "MCP_BATCH_SIZE"]
                    missing_vars = []

                    for var in required_vars:
                        if var not in content:
                            missing_vars.append(var)

                    if missing_vars:
                        self.issues_found.append(f"⚠️  Missing MCP environment variables: {missing_vars}")
                        self.recommendations.append("Add missing MCP environment variables")
                        return False
                    else:
                        logger.info("✅ MCP environment variables configured")
                        return True

                except Exception as e:
                    self.issues_found.append(f"❌ Failed to read MCP env file: {e}")
                    return False

        if not mcp_env_found:
            self.issues_found.append("❌ MCP environment file (.env.mcp) not found")
            self.recommendations.append("Create MCP environment configuration file")
            return False

        return True

    def check_mcp_server_health(self) -> bool:
        """Check MCP server configuration health"""
        logger.info("🔍 Checking MCP server configuration...")

        # Check if MCP server files exist
        mcp_server_files = [
            "scripts/mcp_performance_monitor.py",
            "config/mcp_config_optimized.json"
        ]

        missing_files = []
        for file_path in mcp_server_files:
            if not (self.project_root / file_path).exists():
                missing_files.append(file_path)

        if missing_files:
            self.issues_found.append(f"❌ Missing MCP server files: {missing_files}")
            self.recommendations.append("Create missing MCP server configuration files")
            return False

        logger.info("✅ MCP server files present")
        return True

    def check_recent_logs(self) -> bool:
        """Check for recent error logs"""
        logger.info("🔍 Checking for recent error logs...")

        # Look for recent log files
        log_patterns = ["*.log", "*error*", "*fail*"]
        recent_logs = []

        for pattern in log_patterns:
            for log_file in self.project_root.glob(f"**/{pattern}"):
                if log_file.is_file():
                    try:
                        stat = log_file.stat()
                        # Check if modified in last 24 hours
                        if datetime.now().timestamp() - stat.st_mtime < 86400:
                            recent_logs.append(str(log_file))
                    except:
                        pass

        if recent_logs:
            logger.info(f"📋 Found {len(recent_logs)} recent log files to check")

            # Check for common error patterns
            error_patterns = ["ERROR", "FAILED", "TIMEOUT", "EXCEPTION", "CRASH"]
            error_logs = []

            for log_path in recent_logs[:5]:  # Check first 5 logs
                try:
                    with open(log_path, 'r') as f:
                        content = f.read()
                        for pattern in error_patterns:
                            if pattern in content.upper():
                                error_logs.append(log_path)
                                break
                except:
                    pass

            if error_logs:
                self.issues_found.append(f"⚠️  Error patterns found in logs: {error_logs}")
                self.recommendations.append("Review error logs for specific failure details")
                return False
            else:
                logger.info("✅ No obvious errors in recent logs")
                return True
        else:
            logger.info("ℹ️  No recent log files found")
            return True

    def run_comprehensive_diagnostic(self) -> dict:
        """Run comprehensive diagnostic checks"""
        logger.info("🚀 Starting comprehensive GitHub processing diagnostic...")
        logger.info("=" * 60)

        # Run all diagnostic checks
        checks = [
            ("Timeout Conflicts", self.check_timeout_conflicts),
            ("Workflow Configurations", self.check_workflow_configurations),
            ("Environment Variables", self.check_environment_variables),
            ("MCP Server Health", self.check_mcp_server_health),
            ("Recent Logs", self.check_recent_logs)
        ]

        results = {}
        total_checks = len(checks)
        passed_checks = 0

        for check_name, check_func in checks:
            logger.info(f"\n--- {check_name} ---")
            try:
                result = check_func()
                results[check_name] = result
                if result:
                    passed_checks += 1
            except Exception as e:
                logger.error(f"❌ {check_name} check failed: {e}")
                results[check_name] = False
                self.issues_found.append(f"❌ {check_name} diagnostic failed: {e}")

        # Generate summary report
        summary = self.generate_summary_report(results, passed_checks, total_checks)
        return summary

    def generate_summary_report(self, results: dict, passed: int, total: int) -> dict:
        """Generate comprehensive diagnostic summary"""
        success_rate = (passed / total * 100) if total > 0 else 0

        summary = {
            "timestamp": datetime.now().isoformat(),
            "diagnostic_results": results,
            "success_rate": success_rate,
            "issues_found": self.issues_found,
            "recommendations": self.recommendations,
            "severity_assessment": self.assess_severity(success_rate)
        }

        # Print results
        logger.info("\n" + "=" * 60)
        logger.info("📊 DIAGNOSTIC SUMMARY REPORT")
        logger.info("=" * 60)
        logger.info(f"Success Rate: {passed}/{total} ({success_rate:.1f}%)")
        logger.info(f"Severity: {summary['severity_assessment']}")

        if self.issues_found:
            logger.info("\n🔴 ISSUES FOUND:")
            for issue in self.issues_found:
                logger.info(f"  {issue}")

        if self.recommendations:
            logger.info("\n💡 RECOMMENDATIONS:")
            for rec in self.recommendations:
                logger.info(f"  • {rec}")

        # Save detailed report
        report_path = self.project_root / "github_diagnostic_report.json"
        try:
            with open(report_path, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            logger.info(f"\n✅ Detailed report saved to: {report_path}")
        except Exception as e:
            logger.error(f"❌ Failed to save report: {e}")

        return summary

    def assess_severity(self, success_rate: float) -> str:
        """Assess the severity of issues found"""
        if success_rate >= 90:
            return "LOW - Minor issues, should work"
        elif success_rate >= 70:
            return "MEDIUM - Some issues need attention"
        elif success_rate >= 50:
            return "HIGH - Significant issues found"
        else:
            return "CRITICAL - Major configuration problems"

def main():
    """Main diagnostic function"""
    diagnostic = GitHubDiagnostic()
    summary = diagnostic.run_comprehensive_diagnostic()

    # Exit with appropriate code
    success_rate = summary.get("success_rate", 0)
    if success_rate >= 70:
        logger.info("✅ Diagnostic completed - issues manageable")
        return 0
    else:
        logger.warning("⚠️  Diagnostic completed - attention needed")
        return 1

if __name__ == "__main__":
    sys.exit(main())


