#!/usr/bin/env python3
"""
Deployment Manager for UVAI Video-to-Software Pipeline
======================================================

This module handles deployment of generated projects to various platforms
including GitHub, Vercel, Netlify, and others.
"""

import os
import sys
import asyncio
import logging
import json
import tempfile
import shutil
import zipfile
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import requests
import base64
from datetime import datetime
from youtube_extension.backend.deploy import deploy_project as _adapter_deploy
from .deploy.core import EnvironmentValidator

# Add UVAI paths
uvai_root = Path(__file__).parent.parent.parent.parent
# REMOVED: sys.path.insert for uvai_root

try:
    from src.agents.github_deployment_agent import GitHubDeploymentAgent
except ImportError:
    GitHubDeploymentAgent = None

# Import skill learning system for continuous improvement
try:
    # Add EventRelay root to path for skill_builder
    eventrelay_root = Path(__file__).parent.parent.parent.parent.parent
    sys.path.insert(0, str(eventrelay_root))
    from skill_builder import SkillBuilder
    SKILL_LEARNING_ENABLED = True
except ImportError:
    SkillBuilder = None
    SKILL_LEARNING_ENABLED = False

# Import AI Code Generator for auto-fix capability
try:
    from youtube_extension.backend.ai_code_generator import AICodeGenerator
    AI_CODE_GENERATOR_AVAILABLE = True
except ImportError:
    AICodeGenerator = None
    AI_CODE_GENERATOR_AVAILABLE = False

logger = logging.getLogger(__name__)

class DeploymentManager:
    """
    Manages deployment of generated projects to various platforms
    """

    SUPPORTED_PLATFORMS = ['vercel', 'netlify', 'fly']
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self.github_agent = None

        if self.github_token and GitHubDeploymentAgent:
            try:
                self.github_agent = GitHubDeploymentAgent(self.github_token)
                logger.info("✅ GitHub deployment agent initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize GitHub agent: {e}")

        # Initialize skill learning for continuous improvement
        self.skill_builder = None
        if SKILL_LEARNING_ENABLED and SkillBuilder:
            try:
                self.skill_builder = SkillBuilder()
                stats = self.skill_builder.get_stats()
                logger.info(f"🧠 Skill learning active: {stats['total_errors_handled']} patterns learned")
            except Exception as e:
                logger.warning(f"Failed to initialize skill builder: {e}")

        # Initialize AI code generator for auto-fix capability
        self.ai_code_generator = None
        if AI_CODE_GENERATOR_AVAILABLE and AICodeGenerator:
            try:
                self.ai_code_generator = AICodeGenerator()
                logger.info("🔧 AI auto-fix capability enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize AI code generator: {e}")

    async def verify_project(self, project_path: str) -> Dict[str, Any]:
        """
        Verify generated project builds successfully before deployment.
        Runs npm install and npm run build to catch errors early.
        """
        logger.info("🔍 Verifying project build...")

        result = {
            "passed": False,
            "npm_install": {"success": False, "output": "", "errors": []},
            "npm_build": {"success": False, "output": "", "errors": []},
            "typescript": {"success": False, "errors": []},
            "summary": ""
        }

        project_dir = Path(project_path)
        package_json = project_dir / "package.json"

        # Check if package.json exists
        if not package_json.exists():
            result["summary"] = "No package.json found - skipping verification"
            result["passed"] = True  # Allow non-npm projects
            logger.info("⚠️ No package.json - skipping build verification")
            return result

        try:
            # Run npm install
            logger.info("📦 Running npm install...")
            install_result = subprocess.run(
                ["npm", "install", "--legacy-peer-deps"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=180  # 3 minutes for npm install
            )

            result["npm_install"]["output"] = install_result.stdout
            result["npm_install"]["success"] = install_result.returncode == 0

            if install_result.returncode != 0:
                error_lines = [line for line in install_result.stderr.split('\n') if 'ERR!' in line or 'error' in line.lower()]
                result["npm_install"]["errors"] = error_lines[:10]  # First 10 errors
                result["summary"] = f"npm install failed: {len(error_lines)} errors"
                logger.error(f"❌ npm install failed: {install_result.stderr[:500]}")
                return result

            logger.info("✅ npm install succeeded")

            # Run npm run build
            logger.info("🔨 Running npm run build...")
            build_result = subprocess.run(
                ["npm", "run", "build"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=180
            )

            result["npm_build"]["output"] = build_result.stdout
            result["npm_build"]["success"] = build_result.returncode == 0

            if build_result.returncode != 0:
                # Parse build errors
                error_output = build_result.stderr + build_result.stdout
                error_lines = []
                for line in error_output.split('\n'):
                    if 'error' in line.lower() or 'Error' in line or 'failed' in line.lower():
                        error_lines.append(line.strip())

                result["npm_build"]["errors"] = error_lines[:15]  # First 15 errors
                result["summary"] = f"Build failed: {len(error_lines)} errors found"
                logger.error(f"❌ npm run build failed with {len(error_lines)} errors")

                # Capture errors for learning - will improve future generations
                if self.skill_builder and error_lines:
                    for error in error_lines[:5]:  # Capture first 5 unique errors
                        # Determine error type from content
                        if "Type" in error or "type" in error:
                            error_type = "TypeScriptError"
                        elif "import" in error.lower() or "module" in error.lower():
                            error_type = "ImportError"
                        elif "syntax" in error.lower():
                            error_type = "SyntaxError"
                        else:
                            error_type = "BuildError"

                        # Check if we have a known resolution
                        skill = self.skill_builder.find_matching_skill(error_type, error)
                        if skill:
                            logger.info(f"🧠 Known pattern found: {skill['resolution'][:100]}")
                            result["npm_build"]["suggested_fixes"] = result.get("suggested_fixes", [])
                            result["npm_build"]["suggested_fixes"].append(skill['resolution'])
                        else:
                            # Log for future learning
                            logger.info(f"📝 New error pattern captured for learning: {error_type}")

                return result

            logger.info("✅ npm run build succeeded")

            # Run TypeScript check if tsconfig exists
            tsconfig = project_dir / "tsconfig.json"
            if tsconfig.exists():
                logger.info("🔎 Running TypeScript check...")
                tsc_result = subprocess.run(
                    ["npx", "tsc", "--noEmit"],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                result["typescript"]["success"] = tsc_result.returncode == 0
                if tsc_result.returncode != 0:
                    ts_errors = [line for line in tsc_result.stdout.split('\n') if 'error' in line.lower()]
                    result["typescript"]["errors"] = ts_errors[:10]
                    # Don't fail on TS errors if build passed - they may be warnings
                    logger.warning(f"⚠️ TypeScript has {len(ts_errors)} issues (build passed)")
                else:
                    logger.info("✅ TypeScript check passed")

            # All checks passed
            result["passed"] = True
            result["summary"] = "All verification checks passed"
            logger.info("✅ Project verification complete - ready for deployment")
            return result

        except subprocess.TimeoutExpired as e:
            result["summary"] = f"Verification timeout: {str(e)}"
            logger.error(f"❌ Verification timed out: {e}")
            return result
        except FileNotFoundError:
            result["summary"] = "npm not found - ensure Node.js is installed"
            logger.error("❌ npm command not found")
            return result
        except Exception as e:
            result["summary"] = f"Verification error: {str(e)}"
            logger.error(f"❌ Verification failed: {e}")
            return result

    async def verify_and_fix_project(self, project_path: str, max_retries: int = 2) -> Dict[str, Any]:
        """
        Verify project with automatic AI-powered error fixing and retry.

        Args:
            project_path: Path to the project
            max_retries: Maximum number of fix/retry attempts (default 2)

        Returns:
            Verification result with fix attempts logged
        """
        result = {
            "passed": False,
            "attempts": [],
            "fixes_applied": [],
            "skills_used": []
        }

        for attempt in range(max_retries + 1):
            logger.info(f"🔍 Verification attempt {attempt + 1}/{max_retries + 1}")

            verification = await self.verify_project(project_path)
            result["attempts"].append({
                "attempt": attempt + 1,
                "passed": verification.get("passed", False),
                "errors": verification.get("npm_build", {}).get("errors", [])[:5]
            })

            if verification.get("passed", False):
                result["passed"] = True
                result["final_verification"] = verification

                # Track skill success if we applied fixes
                if attempt > 0 and self.skill_builder and result.get("skills_used"):
                    for skill_id in result["skills_used"]:
                        try:
                            self.skill_builder.apply_skill(skill_id, success=True)
                            logger.info(f"✅ Marked skill {skill_id} as successful")
                        except Exception as e:
                            logger.warning(f"Failed to mark skill success: {e}")

                logger.info(f"✅ Build passed after {attempt + 1} attempt(s)")
                return result

            # If we have more retries and AI fix capability, try to fix
            if attempt < max_retries and self.ai_code_generator:
                errors = verification.get("npm_build", {}).get("errors", [])
                suggested_fixes = verification.get("npm_build", {}).get("suggested_fixes", [])

                if errors:
                    logger.info(f"🔧 Attempting AI auto-fix for {len(errors)} errors...")

                    # Track which skills we're using
                    if self.skill_builder:
                        for error in errors[:3]:
                            skill = self.skill_builder.find_matching_skill("BuildError", error)
                            if skill and skill.get("id"):
                                result["skills_used"].append(skill["id"])

                    try:
                        fix_result = await self.ai_code_generator.fix_build_errors(
                            Path(project_path),
                            errors,
                            suggested_fixes
                        )

                        result["fixes_applied"].append({
                            "attempt": attempt + 1,
                            "success": fix_result.get("success", False),
                            "files_fixed": fix_result.get("fixed_files", [])
                        })

                        if fix_result.get("success"):
                            logger.info(f"✅ Fixed {len(fix_result.get('fixed_files', []))} files, retrying build...")
                        else:
                            logger.warning("⚠️ AI fix attempt did not modify any files")

                    except Exception as e:
                        logger.error(f"❌ AI fix failed: {e}")
                        result["fixes_applied"].append({
                            "attempt": attempt + 1,
                            "success": False,
                            "error": str(e)
                        })
            else:
                # No AI fix capability or no more retries
                if attempt == max_retries:
                    logger.error(f"❌ Build failed after {max_retries + 1} attempts")

        result["final_verification"] = verification
        return result

    async def deploy_project(self, 
                           project_path: str, 
                           project_config: Dict[str, Any],
                           deployment_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deploy a generated project to the specified platforms
        """
        logger.info(f"🚀 Starting deployment: {deployment_config.get('target', 'unknown')}")
        
        results = {
            "deployment_id": f"uvai_{int(asyncio.get_event_loop().time())}",
            "timestamp": datetime.now().isoformat(),
            "project_config": project_config,
            "deployments": {},
            "verification": {},
            "errors": []
        }

        try:
            # Step 0: Verify project builds successfully (with AI auto-fix retry)
            verification_result = await self.verify_and_fix_project(project_path, max_retries=2)
            results["verification"] = verification_result

            if not verification_result.get("passed", False):
                final_ver = verification_result.get("final_verification", {})
                logger.error(f"❌ Project verification failed after {len(verification_result.get('attempts', []))} attempts")
                results["status"] = "failed"
                results["errors"].append(f"Build verification failed after auto-fix attempts")
                results["errors"].extend(final_ver.get("npm_build", {}).get("errors", [])[:5])
                results["auto_fix_attempts"] = verification_result.get("fixes_applied", [])
                return results

            logger.info("✅ Verification passed - proceeding with deployment")

            # Step 1: Deploy to GitHub (always do this first)
            if self.github_token:
                github_result = await self._deploy_to_github(project_path, project_config)
                results["deployments"]["github"] = github_result
            else:
                logger.warning("No GitHub token provided, skipping GitHub deployment")
                results["errors"].append("GitHub token not configured")
            
            # Step 2: Deploy to hosting platforms
            deployment_target = deployment_config.get("target", "vercel")
            github_result = results["deployments"].get("github", {})
            
            if deployment_target in ("vercel", "netlify", "fly"):
                # Start with environment from deployment_config
                adapter_env = deployment_config.get("environment", {}).copy()

                # Override with GitHub URL if GitHub deployment succeeded
                if github_result.get("status") == "success":
                    adapter_env["GITHUB_REPO_URL"] = github_result.get("url")

                try:
                    adapter_result = await _adapter_deploy(deployment_target, project_path, project_config, adapter_env)
                except Exception as e:
                    logger.error(f"{deployment_target} deployment failed: {e}")
                    adapter_result = {"status": "failed", "error": str(e)}
                results["deployments"][deployment_target] = adapter_result
            elif deployment_target == "github_pages":
                pages_result = await self._deploy_to_github_pages(project_path, project_config, github_result)
                results["deployments"]["github_pages"] = pages_result
            elif deployment_target == "github":
                # GitHub repo only - no additional hosting deployment needed
                logger.info("✅ GitHub deployment target: repo created, no hosting deployment")
                # Don't add a hosting entry - GitHub repo is the deployment
                # This prevents triggering partial_success status
            else:
                logger.warning(f"Unknown deployment target: {deployment_target}")
                results["errors"].append(f"Unknown deployment target: {deployment_target}")
            
            # Generate final URLs
            results["urls"] = self._generate_deployment_urls(results["deployments"], project_config)

            # Generate deployment summary
            results["summary"] = self._generate_deployment_summary(results["deployments"])

            # Determine overall status based on deployment results and errors
            has_errors = bool(results["errors"])
            has_failed_deployments = any(
                result.get('status') in ['failed', 'skipped']
                for result in results["deployments"].values()
            )

            if has_errors or has_failed_deployments:
                results["status"] = "failed" if has_errors else "partial_success"
            else:
                results["status"] = "success"

            logger.info(f"✅ Deployment completed: {results['status']}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            results["status"] = "failed"
            results["errors"].append(str(e))
            return results

    def _generate_deployment_summary(self, deployments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of deployment results"""
        total_deployments = len(deployments)
        successful_deployments = sum(1 for result in deployments.values() if result.get('status') == 'success')
        failed_deployments = sum(1 for result in deployments.values() if result.get('status') == 'failed')
        skipped_deployments = sum(1 for result in deployments.values() if result.get('status') == 'skipped')

        # Collect deployment URLs
        deployment_urls = {}
        primary_url = None

        for platform, result in deployments.items():
            if result.get('status') == 'success' and result.get('url'):
                deployment_urls[platform] = result['url']
                if not primary_url:  # Use first successful deployment as primary
                    primary_url = result['url']

        return {
            "total_deployments": total_deployments,
            "successful_deployments": successful_deployments,
            "failed_deployments": failed_deployments,
            "skipped_deployments": skipped_deployments,
            "deployment_urls": deployment_urls,
            "primary_url": primary_url
        }
    
    async def _deploy_to_github(self, project_path: str, project_config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy project to GitHub repository"""
        logger.info("📦 Deploying to GitHub...")

        try:
            if not self.github_token:
                raise Exception("GitHub token not configured")
            
            # Generate repository name
            repo_name = self._generate_repo_name(project_config)
            
            # Create repository
            repo_result = await self._create_github_repository(repo_name, project_config)
            
            # Upload project files
            upload_result = await self._upload_to_github(project_path, repo_result["repo_name"])
            
            return {
                "status": "success",
                "repository": repo_result,
                "upload": upload_result,
                "url": f"https://github.com/{repo_result['owner']}/{repo_result['repo_name']}",
                "clone_url": repo_result.get("clone_url")
            }
            
        except Exception as e:
            logger.error(f"GitHub deployment failed: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def _create_github_repository(self, repo_name: str, project_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new GitHub repository"""
        if not self.github_token:
            raise Exception("GitHub token not configured")
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Get user info
        user_response = requests.get("https://api.github.com/user", headers=headers)
        if user_response.status_code != 200:
            raise Exception(f"Failed to get GitHub user info: {user_response.text}")
        
        user_data = user_response.json()
        username = user_data["login"]
        
        # Create repository
        repo_data = {
            "name": repo_name,
            "description": f"Generated by UVAI from YouTube tutorial - {project_config.get('title', 'Unknown')}",
            "private": False,
            "auto_init": True,
            "has_issues": True,
            "has_projects": True,
            "has_wiki": False
        }
        
        response = requests.post(
            "https://api.github.com/user/repos",
            headers=headers,
            json=repo_data
        )
        
        if response.status_code not in [201, 422]:  # 422 if repo already exists
            raise Exception(f"Failed to create GitHub repository: {response.text}")
        
        if response.status_code == 422:
            # Repository already exists, get its info
            repo_response = requests.get(f"https://api.github.com/repos/{username}/{repo_name}", headers=headers)
            if repo_response.status_code == 200:
                repo_info = repo_response.json()
            else:
                raise Exception(f"Repository exists but can't access it: {repo_response.text}")
        else:
            repo_info = response.json()
        
        return {
            "repo_name": repo_name,
            "owner": username,
            "full_name": repo_info["full_name"],
            "clone_url": repo_info["clone_url"],
            "html_url": repo_info["html_url"]
        }
    
    async def _upload_to_github(self, project_path: str, repo_name: str) -> Dict[str, Any]:
        """Upload project files to GitHub repository"""
        if not self.github_token:
            raise Exception("GitHub token not configured")
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Get user info
        user_response = requests.get("https://api.github.com/user", headers=headers)
        user_data = user_response.json()
        username = user_data["login"]
        
        uploaded_files = []
        project_path_obj = Path(project_path)

        # Directories to exclude from GitHub upload (standard .gitignore patterns)
        EXCLUDED_DIRS = {'node_modules', '.next', '.git', '__pycache__', '.vercel', 'dist', '.turbo'}

        def should_skip_path(path: Path) -> bool:
            """Check if any parent directory is in the exclusion list"""
            return any(part in EXCLUDED_DIRS for part in path.parts)

        # Upload each file
        for file_path in project_path_obj.rglob("*"):
            # Skip excluded directories and dotfiles
            if should_skip_path(file_path.relative_to(project_path_obj)):
                continue
            if file_path.is_file() and not file_path.name.startswith('.'):
                try:
                    relative_path = file_path.relative_to(project_path_obj)
                    
                    # Read file content
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    
                    # Encode content
                    encoded_content = base64.b64encode(content).decode('utf-8')
                    
                    # Upload file
                    file_data = {
                        "message": f"Add {relative_path}",
                        "content": encoded_content
                    }
                    
                    upload_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{relative_path}"
                    response = requests.put(upload_url, headers=headers, json=file_data)
                    
                    if response.status_code in [201, 200]:
                        uploaded_files.append(str(relative_path))
                    else:
                        logger.warning(f"Failed to upload {relative_path}: {response.text}")
                
                except Exception as e:
                    logger.warning(f"Error uploading {file_path}: {e}")
        
        return {
            "files_uploaded": len(uploaded_files),
            "file_list": uploaded_files
        }
    
    # NOTE: legacy _deploy_to_vercel removed; real implementation now in backend.deploy.vercel
    async def _deploy_to_vercel(self, *_args, **_kwargs):
        raise NotImplementedError("_deploy_to_vercel is deprecated – use backend.deploy.vercel adapter")
    
    # NOTE: legacy _deploy_to_netlify removed; see backend.deploy.netlify
    async def _deploy_to_netlify(self, *_args, **_kwargs):
        raise NotImplementedError("_deploy_to_netlify is deprecated – use backend.deploy.netlify adapter")
    
    async def _deploy_to_github_pages(self, project_path: str, project_config: Dict[str, Any], github_result: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy project to GitHub Pages"""
        logger.info("📄 Attempting GitHub Pages deployment...")
        
        try:
            if github_result.get("status") != "success":
                raise Exception("GitHub repository required for GitHub Pages deployment")
            
            repo_info = github_result.get("repository", {})
            owner = repo_info.get("owner")
            repo_name = repo_info.get("repo_name")
            
            if not owner or not repo_name:
                raise Exception("Invalid GitHub repository information")
            
            # Enable GitHub Pages (this would require additional API calls in real implementation)
            pages_url = f"https://{owner}.github.io/{repo_name}"
            
            return {
                "status": "simulated",
                "url": pages_url,
                "message": "GitHub Pages deployment simulated. To enable for real:",
                "instructions": [
                    "1. Go to your GitHub repository settings",
                    "2. Scroll down to 'Pages' section",
                    "3. Select source branch (usually 'main')",
                    "4. Your site will be available at the URL above"
                ],
                "github_repo": repo_info.get("html_url")
            }
            
        except Exception as e:
            logger.error(f"GitHub Pages deployment failed: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _generate_repo_name(self, project_config: Dict[str, Any]) -> str:
        """Generate a repository name from project config"""
        title = project_config.get("title", "uvai-project")
        
        # Sanitize title for repository name
        import re
        name = re.sub(r'[^a-zA-Z0-9\s-]', '', title.lower())
        name = re.sub(r'\s+', '-', name.strip())
        
        # Ensure it's not too long and add timestamp
        name = name[:30]
        timestamp = int(asyncio.get_event_loop().time()) % 10000
        
        return f"{name}-{timestamp}" if name else f"uvai-project-{timestamp}"
    
    def _generate_random_id(self) -> str:
        """Generate a random ID for URLs"""
        import random
        import string
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    def _generate_deployment_urls(self, deployments: Dict[str, Any], project_config: Dict[str, Any]) -> Dict[str, str]:
        """Generate final deployment URLs from all deployment results"""
        urls = {}
        
        for platform, result in deployments.items():
            if result.get("status") in ["success", "simulated"] and result.get("url"):
                urls[platform] = result["url"]
        
        return urls
    
    async def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get the status of a deployment (placeholder for real implementation)"""
        return {
            "deployment_id": deployment_id,
            "status": "completed",
            "message": "Deployment status checking not implemented yet"
        }

# Utility functions
def get_deployment_manager(github_token: Optional[str] = None) -> DeploymentManager:
    """Get or create deployment manager instance"""
    return DeploymentManager(github_token)

def validate_deployment_environment() -> Dict[str, Any]:
    """Validate the deployment environment for all supported platforms"""

    validation_results = {}
    overall_valid = True

    for platform in DeploymentManager.SUPPORTED_PLATFORMS:
        platform_validation = EnvironmentValidator.validate_for_platform(platform)
        validation_results[platform] = platform_validation

        if not platform_validation['valid']:
            overall_valid = False

    # GitHub validation
    github_validation = EnvironmentValidator.validate_for_platform('github')
    validation_results['github'] = github_validation

    return {
        'overall_valid': overall_valid,
        'platform_validations': validation_results,
        'missing_tokens': [
            token for platform, result in validation_results.items()
            for token in result.get('missing_required', [])
        ]
    }