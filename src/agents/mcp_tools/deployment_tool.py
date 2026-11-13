#!/usr/bin/env python3
"""
Deployment MCP Tool - Deploys validated projects to GitHub + Vercel
Automates repo creation, code push, and Vercel deployment
"""

import logging
import os
import subprocess
import traceback
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Failures a deployment step is expected to hit: the CLI is missing or the
# filesystem refuses (OSError), or the subprocess times out / errors
# (subprocess.SubprocessError, which includes TimeoutExpired). Anything else
# is a bug and propagates to the single boundary in deploy_to_github_and_vercel.
STEP_ERRORS: tuple[type[BaseException], ...] = (OSError, subprocess.SubprocessError)


class GitHubIdentityError(RuntimeError):
    """The GitHub owner for a created repo could not be determined."""


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

    def _redact(self, text: str) -> str:
        """Remove configured tokens from text bound for logs or results."""
        for secret in (self.github_token, self.vercel_token):
            if secret:
                # Subprocess exceptions render argv with repr(), escaping e.g.
                # backslashes and newlines before the traceback reaches here.
                for representation in sorted({secret, repr(secret)[1:-1]}, key=len, reverse=True):
                    text = text.replace(representation, "***")
        return text

    def _log_step_failure(self, step: str, exc: BaseException) -> None:
        """Log a failed step with its name, error class and (redacted) traceback.

        The traceback is formatted and redacted here rather than passed as
        exc_info, because subprocess exceptions embed the full command line,
        which carries the Vercel token.
        """
        tb = self._redact("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
        logger.error(
            "Deployment step failed: stage=%s error_class=%s\n%s",
            step,
            type(exc).__name__,
            tb,
            extra={"stage": step, "error_class": type(exc).__name__, "traceback": tb},
        )

    async def deploy_to_github_and_vercel(
        self,
        project_path: str,
        project_name: Optional[str] = None,
        github_org: Optional[str] = None,
        vercel_team: Optional[str] = None
    ) -> dict[str, Any]:
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
        results: dict[str, Any] = {}
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
                results["errors"].append(self._stage_error("git_init", git_init_result))
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
                    results["errors"].append(self._stage_error("github", github_result))
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
                    results["errors"].append(self._stage_error("vercel", vercel_result))
            else:
                if not self.vercel_token:
                    results["errors"].append({
                        "stage": "vercel",
                        "message": "VERCEL_TOKEN not configured"
                    })

            # Determine overall status
            # A completed GitHub artifact is a partial receipt, not proof that
            # the full handoff succeeded when another requested stage failed.
            if not results["errors"] and (results["github_deployed"] or results["vercel_deployed"]):
                results["status"] = "success"
            else:
                results["status"] = "failed"

            return results

        except Exception as exc:  # exception-boundary: MCP tool entry point; the agent network needs a result dict, never a raise
            self._log_step_failure("deploy_entrypoint", exc)
            return {
                **results,
                "status": "error",
                "error": self._redact(str(exc)) or type(exc).__name__,
                "error_class": type(exc).__name__,
                "project_path": project_path
            }

    @staticmethod
    def _stage_error(stage: str, step_result: dict[str, Any]) -> dict[str, Any]:
        entry = {"stage": stage, "message": step_result["error"]}
        if step_result.get("error_class"):
            entry["error_class"] = step_result["error_class"]
        return entry

    async def _initialize_git(self, project_dir: Path) -> dict[str, Any]:
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
                return {"success": False, "error": self._redact(result.stderr)}

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
            add_result = subprocess.run(
                ["git", "add", "."],
                cwd=str(project_dir),
                capture_output=True,
                timeout=30
            )

            if add_result.returncode != 0:
                logger.error("Deployment handoff failed", extra={"stage": "git_add", "returncode": add_result.returncode})
                return {"success": False, "error": "Git staging failed"}

            commit_result = subprocess.run(
                ["git", "commit", "-m", "Initial commit - AI generated project"],
                cwd=str(project_dir),
                capture_output=True,
                timeout=30
            )

            if commit_result.returncode != 0:
                logger.error("Deployment handoff failed", extra={"stage": "git_commit", "returncode": commit_result.returncode})
                return {"success": False, "error": "Git initial commit failed"}

            logger.info("✅ Git initialized")
            return {"success": True}

        except subprocess.TimeoutExpired as exc:
            self._log_step_failure("git_init", exc)
            return {"success": False, "error": "Git initialization timed out", "error_class": type(exc).__name__}
        except STEP_ERRORS as exc:
            self._log_step_failure("git_init", exc)
            return {"success": False, "error": f"Git initialization failed: {type(exc).__name__}", "error_class": type(exc).__name__}

    async def _create_github_repo(
        self,
        project_dir: Path,
        repo_name: str,
        github_org: Optional[str]
    ) -> dict[str, Any]:
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
                error_msg = self._redact(result.stderr or result.stdout)
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
                # Construct URL from repo name. The org, when given, is the owner;
                # otherwise the authenticated user is, and if that cannot be
                # looked up the URL is unknown - never guessed.
                if github_org:
                    owner = github_org
                else:
                    try:
                        owner = self._get_github_username()
                    except GitHubIdentityError as exc:
                        self._log_step_failure("github_identity", exc)
                        return {
                            "success": False,
                            "error": "GitHub owner lookup failed; repo URL could not be verified",
                            "error_class": type(exc).__name__,
                        }
                repo_url = f"https://github.com/{owner}/{repo_name}"

            return {
                "success": True,
                "repo_url": repo_url
            }

        except subprocess.TimeoutExpired as exc:
            self._log_step_failure("github", exc)
            return {"success": False, "error": "GitHub repo creation timed out", "error_class": type(exc).__name__}
        except STEP_ERRORS as exc:
            self._log_step_failure("github", exc)
            return {"success": False, "error": f"GitHub repo creation failed: {type(exc).__name__}", "error_class": type(exc).__name__}

    async def _deploy_to_vercel(
        self,
        project_dir: Path,
        project_name: str,
        vercel_team: Optional[str]
    ) -> dict[str, Any]:
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
                error_msg = self._redact(result.stderr or result.stdout)
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
                logger.error("Deployment output lacked verified URL", extra={"stage": "vercel_output"})
                return {"success": False, "error": "Vercel returned no verified deployment URL"}

            return {
                "success": True,
                "deployment_url": deployment_url
            }

        except subprocess.TimeoutExpired as exc:
            self._log_step_failure("vercel", exc)
            return {"success": False, "error": "Vercel deployment timed out (>5min)", "error_class": type(exc).__name__}
        except STEP_ERRORS as exc:
            self._log_step_failure("vercel", exc)
            return {"success": False, "error": f"Vercel deployment failed: {type(exc).__name__}", "error_class": type(exc).__name__}

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
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.error("GitHub identity lookup failed", extra={"stage": "github_identity", "error_class": type(exc).__name__})
            raise GitHubIdentityError("GitHub identity lookup failed") from exc
        logger.error("GitHub identity lookup failed", extra={"stage": "github_identity", "returncode": result.returncode})
        raise GitHubIdentityError("GitHub identity lookup failed")


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

