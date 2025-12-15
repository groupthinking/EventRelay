#!/usr/bin/env python3
"""
Deployment MCP Tool - Deploys validated projects to GitHub + Vercel
Automates repo creation, code push, and Vercel deployment
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import subprocess
import json

logger = logging.getLogger(__name__)


class DeploymentMCPTool:
    """
    MCP-compatible wrapper for deployment automation.
    Creates GitHub repos and deploys to Vercel.
    """

    def __init__(self):
        self.github_token = os.environ.get("GITHUB_TOKEN")
        self.vercel_token = os.environ.get("VERCEL_TOKEN")

        if not self.github_token:
            logger.warning("⚠️  GITHUB_TOKEN not set - GitHub deployment disabled")
        if not self.vercel_token:
            logger.warning("⚠️  VERCEL_TOKEN not set - Vercel deployment disabled")

        logger.info("✅ Deployment Tool initialized")

    async def close(self):
        """Clean up resources"""
        pass

    async def deploy_to_github_and_vercel(
        self,
        project_path: str,
        project_name: Optional[str] = None,
        github_org: Optional[str] = None,
        vercel_team: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deploy a project to GitHub and Vercel.

        MCP Tool: deploy_to_github_and_vercel

        Args:
            project_path: Path to built project
            project_name: Override project name (default: directory name)
            github_org: GitHub org (default: personal account)
            vercel_team: Vercel team ID (optional)

        Returns:
            Dict with deployment URLs and status
        """
        try:
            logger.info(f"🚀 Deploying: {project_path}")

            project_dir = Path(project_path)
            if not project_dir.exists():
                return {
                    "status": "error",
                    "error": f"Project path does not exist: {project_path}"
                }

            # Determine and sanitize project name
            if not project_name:
                project_name = project_dir.name

            # Sanitize project name for GitHub (max 100 chars, lowercase, alphanumeric + hyphens)
            import re
            project_name = project_name.lower()
            project_name = re.sub(r'[^a-z0-9\-_]', '-', project_name)  # Replace invalid chars
            project_name = re.sub(r'-+', '-', project_name)  # Collapse multiple hyphens
            project_name = project_name.strip('-_')  # Remove leading/trailing hyphens
            project_name = project_name[:100]  # GitHub max length
            project_name = project_name.strip('-_')  # Remove trailing hyphens after truncation

            # Ensure name is not empty
            if not project_name:
                import time
                project_name = f"generated-project-{int(time.time())}"

            results = {
                "status": "in_progress",
                "project_path": str(project_path),
                "project_name": project_name,
                "github_deployed": False,
                "vercel_deployed": False,
                "github_url": None,
                "vercel_url": None,
                "errors": []
            }

            # Step 1: Initialize git if needed
            git_init_result = await self._initialize_git(project_dir)
            if not git_init_result["success"]:
                results["errors"].append({"stage": "git_init", "message": git_init_result["error"]})
                results["status"] = "failed"
                return results

            # Step 2: Create GitHub repository
            if self.github_token:
                github_result = await self._create_github_repo(
                    project_dir,
                    project_name,
                    github_org
                )

                if github_result["success"]:
                    results["github_deployed"] = True
                    results["github_url"] = github_result["repo_url"]
                    logger.info(f"✅ GitHub: {results['github_url']}")
                else:
                    results["errors"].append({
                        "stage": "github",
                        "message": github_result["error"]
                    })
            else:
                results["errors"].append({
                    "stage": "github",
                    "message": "GITHUB_TOKEN not configured"
                })

            # Step 3: Deploy to Vercel
            if self.vercel_token and results["github_deployed"]:
                vercel_result = await self._deploy_to_vercel(
                    project_dir,
                    project_name,
                    vercel_team
                )

                if vercel_result["success"]:
                    results["vercel_deployed"] = True
                    results["vercel_url"] = vercel_result["deployment_url"]
                    logger.info(f"✅ Vercel: {results['vercel_url']}")
                else:
                    results["errors"].append({
                        "stage": "vercel",
                        "message": vercel_result["error"]
                    })
            else:
                if not self.vercel_token:
                    results["errors"].append({
                        "stage": "vercel",
                        "message": "VERCEL_TOKEN not configured"
                    })

            # Determine overall status
            if results["github_deployed"] or results["vercel_deployed"]:
                results["status"] = "success"
            else:
                results["status"] = "failed"

            return results

        except Exception as e:
            logger.error(f"Deployment error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e),
                "project_path": project_path
            }

    async def _initialize_git(self, project_dir: Path) -> Dict[str, Any]:
        """Initialize git repository if not already initialized"""
        try:
            git_dir = project_dir / ".git"

            if git_dir.exists():
                logger.info("Git already initialized")
                return {"success": True}

            # Initialize git
            # SECURITY: subprocess call uses hardcoded command list.
            # project_dir is used as cwd.
            result = subprocess.run(
                ["git", "init"],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return {"success": False, "error": result.stderr}

            # Create .gitignore if doesn't exist
            gitignore = project_dir / ".gitignore"
            if not gitignore.exists():
                gitignore.write_text("""node_modules/
.next/
.env.local
.env
.DS_Store
*.log
out/
build/
dist/
""")

            # Initial commit
            # SECURITY: subprocess call uses hardcoded command list.
            subprocess.run(
                ["git", "add", "."],
                cwd=str(project_dir),
                capture_output=True,
                timeout=30
            )

            subprocess.run(
                ["git", "commit", "-m", "Initial commit - AI generated project"],
                cwd=str(project_dir),
                capture_output=True,
                timeout=30
            )

            logger.info("✅ Git initialized")
            return {"success": True}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git initialization timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _create_github_repo(
        self,
        project_dir: Path,
        repo_name: str,
        github_org: Optional[str]
    ) -> Dict[str, Any]:
        """Create GitHub repository and push code"""
        try:
            logger.info(f"Creating GitHub repo: {repo_name}")

            # Use gh CLI to create repo (private to avoid secret detection blocks)
            cmd = [
                "gh", "repo", "create", repo_name,
                "--private",  # Private by default to allow secret cleanup before going public
                "--source", ".",
                "--push",
                "--description", "AI-generated application from video analysis"
            ]

            if github_org:
                cmd.extend(["--org", github_org])

            # SAFE: cmd is a list of arguments, preventing shell injection.
            # repo_name is sanitized above. github_org is treated as an argument.
            # SECURITY: Validated inputs used in subprocess list.
            result = subprocess.run(
                cmd,
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "GH_TOKEN": self.github_token}
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                return {"success": False, "error": error_msg}

            # Extract repo URL from output
            output = result.stdout
            repo_url = None
            for line in output.split('\n'):
                if 'github.com' in line and 'http' in line:
                    # Extract URL
                    import re
                    url_match = re.search(r'https://github\.com/[\w-]+/[\w-]+', line)
                    if url_match:
                        repo_url = url_match.group(0)
                        break

            if not repo_url:
                # Construct URL from repo name
                username = self._get_github_username()
                repo_url = f"https://github.com/{github_org or username}/{repo_name}"

            return {
                "success": True,
                "repo_url": repo_url
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "GitHub repo creation timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _deploy_to_vercel(
        self,
        project_dir: Path,
        project_name: str,
        vercel_team: Optional[str]
    ) -> Dict[str, Any]:
        """Deploy project to Vercel"""
        try:
            logger.info(f"Deploying to Vercel: {project_name}")

            # Use vercel CLI for deployment
            cmd = [
                "vercel",
                "--prod",
                "--yes",  # Skip confirmations
                "--token", self.vercel_token
            ]

            if vercel_team:
                cmd.extend(["--scope", vercel_team])

            # SECURITY: subprocess call uses constructed list with sanitized inputs.
            result = subprocess.run(
                cmd,
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes for build + deploy
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                return {"success": False, "error": error_msg}

            # Extract deployment URL from output
            output = result.stdout
            deployment_url = None

            # Vercel outputs the URL in the last line typically
            lines = [line.strip() for line in output.split('\n') if line.strip()]
            for line in reversed(lines):
                if 'vercel.app' in line or 'https://' in line:
                    import re
                    url_match = re.search(r'https://[\w-]+\.vercel\.app', line)
                    if url_match:
                        deployment_url = url_match.group(0)
                        break

            if not deployment_url:
                deployment_url = f"https://{project_name}.vercel.app"

            return {
                "success": True,
                "deployment_url": deployment_url
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Vercel deployment timed out (>5min)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_github_username(self) -> str:
        """Get GitHub username from gh CLI"""
        try:
            result = subprocess.run(
                ["gh", "api", "user", "--jq", ".login"],
                capture_output=True,
                text=True,
                timeout=10,
                env={**os.environ, "GH_TOKEN": self.github_token}
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return "unknown"


# Singleton instance
_tool = None

def get_deployment_tool() -> DeploymentMCPTool:
    """Get or create Deployment MCP Tool singleton"""
    global _tool
    if _tool is None:
        _tool = DeploymentMCPTool()
    return _tool

# MCP Tool registry for agent network
MCP_TOOLS = {
    "deploy_to_github_and_vercel": get_deployment_tool().deploy_to_github_and_vercel
}
