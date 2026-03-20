#!/usr/bin/env python3
"""
AI Tools Installation Verification Script

This script verifies the installation and configuration status of:
- GitHub Copilot
- Cursor AI
- Development environment setup
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


class AIToolsVerifier:
    def __init__(self, repo_path: str = ".") -> None:
        self.repo_path = Path(repo_path).resolve()
        self.results = {
            "github_copilot": {},
            "cursor_ai": {},
            "development_environment": {},
            "overall_status": "unknown"
        }

    def check_github_copilot(self) -> Dict[str, Any]:
        """Check GitHub Copilot configuration and availability"""
        copilot_status = {
            "instructions_file": False,
            "instructions_content": None,
            "gh_cli_available": False,
            "github_integration": False
        }

        # Check for copilot instructions file
        instructions_path = self.repo_path / ".github" / "copilot-instructions.md"
        if instructions_path.exists():
            copilot_status["instructions_file"] = True
            with open(instructions_path, 'r') as f:
                content = f.read()
                copilot_status["instructions_content"] = len(content)
                copilot_status["has_comprehensive_guide"] = "YouTube AI Extension Development Guide" in content

        # Check if gh CLI is available
        try:
            result = subprocess.run(['which', 'gh'], capture_output=True, text=True)
            if result.returncode == 0:
                copilot_status["gh_cli_available"] = True
                # Check if gh copilot extension is available
                try:
                    gh_result = subprocess.run(['gh', 'extension', 'list'], capture_output=True, text=True)
                    copilot_status["gh_extensions"] = gh_result.stdout if gh_result.returncode == 0 else "error"
                except:
                    copilot_status["gh_extensions"] = "unavailable"
        except:
            pass

        return copilot_status

    def check_cursor_ai(self) -> Dict[str, Any]:
        """Check Cursor AI configuration"""
        cursor_status = {
            "cursor_directory": False,
            "environment_config": False,
            "rules_configured": False,
            "rules_count": 0,
            "cursorignore_present": False
        }

        # Check .cursor directory
        cursor_dir = self.repo_path / ".cursor"
        if cursor_dir.exists() and cursor_dir.is_dir():
            cursor_status["cursor_directory"] = True

            # Check environment.json
            env_file = cursor_dir / "environment.json"
            if env_file.exists():
                cursor_status["environment_config"] = True
                try:
                    with open(env_file, 'r') as f:
                        env_data = json.load(f)
                        cursor_status["environment_data"] = env_data
                except:
                    cursor_status["environment_data"] = "invalid_json"

            # Check rules directory
            rules_dir = cursor_dir / "rules"
            if rules_dir.exists() and rules_dir.is_dir():
                cursor_status["rules_configured"] = True
                rule_files = list(rules_dir.glob("*.mdc"))
                cursor_status["rules_count"] = len(rule_files)
                cursor_status["rule_files"] = [f.name for f in rule_files]

        # Check .cursorignore
        cursorignore_path = self.repo_path / ".cursorignore"
        if cursorignore_path.exists():
            cursor_status["cursorignore_present"] = True
            with open(cursorignore_path, 'r') as f:
                cursor_status["cursorignore_content"] = f.read().strip()

        return cursor_status

    def check_development_environment(self) -> Dict[str, Any]:
        """Check development environment setup"""
        dev_status = {
            "python_version": None,
            "node_version": None,
            "npm_version": None,
            "build_system": False,
            "vscode_workspace": False,
            "package_configs": []
        }

        # Check Python version
        try:
            result = subprocess.run(['python3', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                dev_status["python_version"] = result.stdout.strip()
        except:
            pass

        # Check Node.js version
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                dev_status["node_version"] = result.stdout.strip()
        except:
            pass

        # Check npm version
        try:
            result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                dev_status["npm_version"] = result.stdout.strip()
        except:
            pass

        # Check build system
        build_script = self.repo_path / "scripts" / "build.py"
        if build_script.exists():
            dev_status["build_system"] = True
            try:
                result = subprocess.run(['python3', str(build_script), '--help'],
                                      capture_output=True, text=True, cwd=self.repo_path)
                dev_status["build_system_working"] = result.returncode == 0
            except:
                dev_status["build_system_working"] = False

        # Check VS Code workspace
        workspace_files = list(self.repo_path.glob("*.code-workspace"))
        if workspace_files:
            dev_status["vscode_workspace"] = True
            dev_status["workspace_files"] = [f.name for f in workspace_files]

        # Check package configuration files
        config_files = ["pyproject.toml", "package.json", "requirements.txt"]
        for config_file in config_files:
            if (self.repo_path / config_file).exists():
                dev_status["package_configs"].append(config_file)

        return dev_status

    def determine_overall_status(self) -> str:
        """Determine overall installation status"""
        copilot = self.results["github_copilot"]
        cursor = self.results["cursor_ai"]
        dev = self.results["development_environment"]

        # Check critical components
        has_copilot_config = copilot.get("instructions_file", False)
        has_cursor_config = cursor.get("cursor_directory", False) and cursor.get("rules_configured", False)
        has_dev_env = (dev.get("python_version") is not None and
                      dev.get("node_version") is not None and
                      dev.get("build_system", False))

        if has_copilot_config and has_cursor_config and has_dev_env:
            return "fully_configured"
        elif has_copilot_config or has_cursor_config:
            return "partially_configured"
        else:
            return "not_configured"

    def run_verification(self) -> Dict[str, Any]:
        """Run complete verification process"""
        print("🔍 Verifying AI Tools Installation and Configuration...")
        print(f"📁 Repository: {self.repo_path}")
        print()

        # Run checks
        self.results["github_copilot"] = self.check_github_copilot()
        self.results["cursor_ai"] = self.check_cursor_ai()
        self.results["development_environment"] = self.check_development_environment()
        self.results["overall_status"] = self.determine_overall_status()

        return self.results

    def print_report(self) -> None:
        """Print comprehensive verification report"""
        print("=" * 80)
        print("🤖 AI TOOLS VERIFICATION REPORT")
        print("=" * 80)

        # Overall Status
        status_emoji = {
            "fully_configured": "✅",
            "partially_configured": "⚠️",
            "not_configured": "❌"
        }

        overall_status = self.results["overall_status"]
        print(f"\n📊 Overall Status: {status_emoji.get(overall_status, '❓')} {overall_status.replace('_', ' ').title()}")
        print()

        # GitHub Copilot Section
        print("🔧 GITHUB COPILOT")
        print("-" * 20)
        copilot = self.results["github_copilot"]

        print(f"✓ Instructions File: {'✅' if copilot.get('instructions_file') else '❌'}")
        if copilot.get('instructions_content'):
            print(f"  📄 Content Length: {copilot['instructions_content']} characters")
        if copilot.get('has_comprehensive_guide'):
            print(f"  📋 Comprehensive Guide: ✅")

        print(f"✓ GitHub CLI Available: {'✅' if copilot.get('gh_cli_available') else '❌'}")

        print()

        # Cursor AI Section
        print("🎯 CURSOR AI")
        print("-" * 15)
        cursor = self.results["cursor_ai"]

        print(f"✓ .cursor Directory: {'✅' if cursor.get('cursor_directory') else '❌'}")
        print(f"✓ Environment Config: {'✅' if cursor.get('environment_config') else '❌'}")
        print(f"✓ Rules Configured: {'✅' if cursor.get('rules_configured') else '❌'}")

        if cursor.get('rules_count', 0) > 0:
            print(f"  📁 Rules Count: {cursor['rules_count']}")
            print(f"  📝 Rule Files: {', '.join(cursor.get('rule_files', []))}")

        print(f"✓ .cursorignore Present: {'✅' if cursor.get('cursorignore_present') else '❌'}")

        print()

        # Development Environment Section
        print("🛠️ DEVELOPMENT ENVIRONMENT")
        print("-" * 25)
        dev = self.results["development_environment"]

        print(f"🐍 Python: {dev.get('python_version', '❌ Not found')}")
        print(f"📦 Node.js: {dev.get('node_version', '❌ Not found')}")
        print(f"📦 npm: {dev.get('npm_version', '❌ Not found')}")
        print(f"🔨 Build System: {'✅ Working' if dev.get('build_system_working') else '❌ Not working' if dev.get('build_system') else '❌ Not found'}")
        print(f"💼 VS Code Workspace: {'✅' if dev.get('vscode_workspace') else '❌'}")

        if dev.get('package_configs'):
            print(f"📋 Package Configs: {', '.join(dev['package_configs'])}")

        print()

        # Recommendations
        print("💡 RECOMMENDATIONS")
        print("-" * 18)

        if overall_status == "fully_configured":
            print("🎉 All AI tools are properly configured!")
            print("   • GitHub Copilot instructions are comprehensive")
            print("   • Cursor AI rules and environment are set up")
            print("   • Development environment is ready")
        elif overall_status == "partially_configured":
            print("⚠️  Some components need attention:")
            if not copilot.get('instructions_file'):
                print("   • Add GitHub Copilot instructions file")
            if not cursor.get('cursor_directory'):
                print("   • Set up Cursor AI configuration directory")
            if not dev.get('build_system_working'):
                print("   • Fix build system configuration")
        else:
            print("❌ AI tools need to be configured:")
            print("   • Set up GitHub Copilot instructions")
            print("   • Configure Cursor AI environment")
            print("   • Verify development environment setup")

        print()
        print("=" * 80)

def main() -> None:
    """Main entry point"""
    repo_path = os.getcwd()

    verifier = AIToolsVerifier(repo_path)
    results = verifier.run_verification()
    verifier.print_report()

    # Return appropriate exit code
    overall_status = results["overall_status"]
    if overall_status == "fully_configured":
        sys.exit(0)
    elif overall_status == "partially_configured":
        sys.exit(1)
    else:
        sys.exit(2)

if __name__ == "__main__":
    main()
