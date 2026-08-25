#!/usr/bin/env python3
"""
Vercel deployment adapter for UVAI platform.
Updated to use new base adapter architecture with retry logic and proper error handling.
"""

from typing import Any, Optional

from .core import (
    BaseDeploymentAdapter,
    DeploymentError,
    DeploymentResult,
    EnvironmentValidator,
)

VERCEL_API = "https://api.vercel.com"

class VercelAdapter(BaseDeploymentAdapter):
    """Vercel deployment adapter with enhanced error handling and monitoring"""

    def __init__(self):
        super().__init__('vercel')

    @staticmethod
    def _ensure_https(url: Optional[str]) -> Optional[str]:
        """Ensure URL has https:// prefix (Vercel API returns bare domains)"""
        if not url:
            return None
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return f"https://{url}"

    @staticmethod
    def _vercel_import_url(org: str, repo_name: str) -> str:
        """Generate a Vercel import URL the user can click to deploy manually"""
        return f"https://vercel.com/new/import?s=https://github.com/{org}/{repo_name}"

    async def _deploy_impl(self, project_path: str, project_config: dict[str, Any], env: dict[str, Any]) -> DeploymentResult:
        """Vercel-specific deployment implementation"""

        # Get and validate GitHub repository URL
        repo_url = env.get("GITHUB_REPO_URL")
        if not repo_url:
            raise DeploymentError(
                platform=self.platform,
                operation='validation',
                message="GITHUB_REPO_URL required for Vercel deployment"
            )

        # Get Vercel token
        token = EnvironmentValidator.get_token('VERCEL_TOKEN')
        if not token:
            raise DeploymentError(
                platform=self.platform,
                operation='validation',
                message="VERCEL_TOKEN not configured"
            )

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Parse org/repo from GitHub URL
        repo_path = repo_url.replace("https://github.com/", "").strip("/")
        parts = repo_path.split("/")
        if len(parts) >= 2:
            org, repo_name = parts[0], parts[1]
        else:
            org, repo_name = "groupthinking", repo_path

        project_name = env.get(
            "VERCEL_PROJECT_NAME",
            f"uvai-{project_config.get('title', 'project').lower().replace(' ', '-')}"
        )

        # Prepare deployment payload using Vercel REST API v13 gitSource format
        payload = {
            "name": project_name,
            "gitSource": {
                "type": "github",
                "org": org,
                "repo": repo_name,
                "ref": project_config.get("branch", "main")
            },
            "projectSettings": {
                "framework": self._detect_framework(project_config),
                "installCommand": project_config.get("install_command", "npm install || true"),
                "buildCommand": project_config.get("build_command", "echo 'static'"),
                "outputDirectory": project_config.get("output_directory", ".")
            }
        }

        # Optionally scope to a Vercel team
        team_id = EnvironmentValidator.get_token('VERCEL_ORG_ID')
        api_url = f"{VERCEL_API}/v13/deployments"
        if team_id:
            api_url = f"{api_url}?teamId={team_id}"

        # Create deployment
        self.logger.info(f"Creating Vercel deployment for {project_name}")
        try:
            deployment_data = await self._make_request_with_retry(
                'POST',
                api_url,
                headers=headers,
                json_data=payload,
                timeout=120.0
            )
        except DeploymentError as e:
            # If API deployment fails (permissions, plan limits, etc.)
            # return a manual-import fallback URL so the user isn't stuck
            self.logger.warning(f"Vercel API deployment failed: {e.message}")
            import_url = self._vercel_import_url(org, repo_name)
            return DeploymentResult(
                status='failed',
                platform=self.platform,
                # `url` is reserved for a URL that actually serves the app.
                # A manual-import link is a call to action, not a running
                # site; returning it here made every downstream consumer
                # report a failed deploy as a live deployment.
                url=None,
                error_message=f"API deployment failed: {e.message}. Use the import URL to deploy manually.",
                build_log_url=import_url,
                metadata={
                    'project_name': project_name,
                    'action_required': 'manual_import',
                    'import_url': import_url,
                    'api_error': e.message,
                    'api_details': e.details,
                }
            )

        deployment_id = deployment_data.get('id')
        deployment_url = self._ensure_https(deployment_data.get('url'))

        if not deployment_id:
            import_url = self._vercel_import_url(org, repo_name)
            return DeploymentResult(
                status='failed',
                platform=self.platform,
                url=None,
                error_message="Vercel deployment creation returned no deployment ID. Use the import URL to deploy manually.",
                build_log_url=import_url,
                metadata={
                    'project_name': project_name,
                    'action_required': 'manual_import',
                    'import_url': import_url,
                    'deployment_response': deployment_data,
                }
            )

        # Poll for deployment completion
        inspector_url = f"https://vercel.com/{project_name}/{deployment_id}"
        ready = deployment_data.get('readyState', deployment_data.get('status', ''))
        if ready.upper() != 'READY':
            status_url = f"{VERCEL_API}/v13/deployments/{deployment_id}"
            if team_id:
                status_url = f"{status_url}?teamId={team_id}"
            self.logger.info(f"Polling Vercel deployment status: {deployment_id}")

            try:
                final_status = await self._poll_deployment_status(
                    status_url,
                    headers=headers,
                    success_statuses=['READY'],
                    timeout_minutes=15
                )
                deployment_url = self._ensure_https(final_status.get('url', '')) or deployment_url
            except DeploymentError as poll_err:
                # A deployment that never reached READY is not a success.
                # Previously this fell through and returned status='success'
                # with a guessed <project>.vercel.app URL that may 404 or
                # serve a stale build, which is how build failures and
                # timeouts were reported as live deployments.
                self.logger.error(
                    f"Vercel deployment {deployment_id} never reached READY: {poll_err.message}"
                )
                return DeploymentResult(
                    status='failed',
                    platform=self.platform,
                    deployment_id=deployment_id,
                    url=None,
                    error_message=(
                        f"Deployment did not reach READY state: {poll_err.message}"
                    ),
                    build_log_url=inspector_url,
                    metadata={
                        'project_name': project_name,
                        'action_required': 'inspect_build_logs',
                        'last_known_url': deployment_url,
                        'poll_error': poll_err.message,
                        'deployment_data': deployment_data,
                    }
                )

        # A READY deployment must expose a real URL. Guessing the hostname
        # here would reintroduce unverified URLs, so treat this as a failure.
        if not deployment_url:
            self.logger.error(
                f"Vercel deployment {deployment_id} reported READY without a URL"
            )
            return DeploymentResult(
                status='failed',
                platform=self.platform,
                deployment_id=deployment_id,
                url=None,
                error_message="Deployment reached READY but returned no URL.",
                build_log_url=inspector_url,
                metadata={
                    'project_name': project_name,
                    'action_required': 'inspect_build_logs',
                    'deployment_data': deployment_data,
                }
            )

        return DeploymentResult(
            status='success',
            platform=self.platform,
            deployment_id=deployment_id,
            url=deployment_url,
            build_log_url=inspector_url,
            metadata={
                'project_name': project_name,
                'framework': self._detect_framework(project_config),
                'verified_ready': True,
                'deployment_data': deployment_data
            }
        )

    def _detect_framework(self, project_config: dict[str, Any]) -> Optional[str]:
        """Detect framework from project configuration"""

        # Check for explicit framework specification
        framework = project_config.get('framework')
        if framework:
            return framework.lower()

        # Try to detect from files/project structure
        project_type = project_config.get('project_type', '').lower()

        framework_mapping = {
            'react': 'nextjs',
            'next': 'nextjs',
            'vue': 'vue',
            'angular': 'angular',
            'svelte': 'svelte',
            'nuxt': 'nuxtjs',
            'astro': 'astro',
            'web': 'nextjs',  # Default for web projects
            'static': None,   # Static sites don't need framework detection
        }

        return framework_mapping.get(project_type)

# Legacy function for backward compatibility
async def deploy(project_path: str, project_config: dict[str, Any], env: dict[str, Any]) -> dict[str, Any]:
    """Legacy deployment function - use VercelAdapter for new code"""
    adapter = VercelAdapter()
    result = await adapter.deploy(project_path, project_config, env)

    # Convert to legacy format for backward compatibility
    return {
        "status": result.status,
        "deployment_id": result.deployment_id,
        "url": result.url,
        "inspector_url": result.build_log_url,
        "platform": result.platform,
        "error": result.error_message,
        **result.metadata
    }
