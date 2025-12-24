#!/usr/bin/env python3
"""
Netlify deployment adapter for UVAI platform.
Updated to use new base adapter architecture with retry logic and proper error handling.
"""

import os
from typing import Dict, Any, Optional
from .core import BaseDeploymentAdapter, DeploymentResult, EnvironmentValidator, DeploymentError

NETLIFY_API = "https://api.netlify.com/api/v1"

class NetlifyAdapter(BaseDeploymentAdapter):
    """Netlify deployment adapter with enhanced error handling and monitoring"""

    def __init__(self):
        super().__init__('netlify')

    async def _deploy_impl(self, project_path: str, project_config: Dict[str, Any], env: Dict[str, Any]) -> DeploymentResult:
        """Netlify-specific deployment implementation"""

        # Get and validate GitHub repository URL
        repo_url = env.get("GITHUB_REPO_URL")
        if not repo_url:
            raise DeploymentError(
                platform=self.platform,
                operation='validation',
                message="GITHUB_REPO_URL required for Netlify deployment"
            )

        # Get Netlify token
        token = EnvironmentValidator.get_token('NETLIFY_AUTH_TOKEN')
        if not token:
            raise DeploymentError(
                platform=self.platform,
                operation='validation',
                message="NETLIFY_AUTH_TOKEN not configured"
            )

        headers = {"Authorization": f"Bearer {token}"}

        # Create or get existing site
        site_name = env.get("NETLIFY_SITE_NAME") or f"uvai-{project_config.get('title', 'project').lower().replace(' ', '-')}"
        self.logger.info(f"Setting up Netlify site: {site_name}")

        site = await self._create_or_get_site(headers, site_name)

        # Configure build settings
        build_settings = self._get_build_settings(project_config)
        await self._configure_site_build_settings(headers, site['id'], build_settings)

        # Trigger deployment
        self.logger.info(f"Triggering Netlify deployment for site: {site['id']}")
        deploy_data = await self._trigger_deployment(headers, site, repo_url)

        deploy_id = deploy_data.get('id')

        if not deploy_id:
            raise DeploymentError(
                platform=self.platform,
                operation='create_deployment',
                message="Netlify deployment creation failed - no deployment ID returned",
                details=deploy_data
            )

        # Poll for deployment completion (Netlify deployments can take time)
        if deploy_data.get('state') != 'ready':
            deploy_url = f"{NETLIFY_API}/sites/{site['id']}/deploys/{deploy_id}"
            self.logger.info(f"Polling Netlify deployment status: {deploy_id}")

            final_status = await self._poll_deployment_status(
                deploy_url,
                success_statuses=['ready'],
                timeout_minutes=20  # Netlify builds can take longer
            )

            site_url = site.get('url') or final_status.get('url', site.get('admin_url', ''))

        return DeploymentResult(
            status='success',
            platform=self.platform,
            deployment_id=deploy_id,
            url=site.get('url') or site.get('admin_url'),
            build_log_url=f"https://app.netlify.com/sites/{site_name}/deploys/{deploy_id}",
            metadata={
                'site_name': site_name,
                'site_id': site['id'],
                'build_settings': build_settings,
                'deployment_data': deploy_data
            }
        )

    async def _create_or_get_site(self, headers: Dict[str, str], site_name: str) -> Dict[str, Any]:
        """Create a new site or get existing one"""

        # Try to get existing site first
        try:
            site_data = await self._make_request_with_retry(
                'GET',
                f"{NETLIFY_API}/sites/{site_name}",
                headers=headers
            )
            self.logger.info(f"Using existing Netlify site: {site_name}")
            return site_data
        except DeploymentError:
            # Site doesn't exist, create new one
            pass

        # Create new site
        payload = {
            "name": site_name,
            "build_settings": {
                "repo_url": "https://github.com/placeholder/placeholder",  # Will be updated during deploy
                "repo_branch": "main",
                "build_command": "npm run build",
                "publish_dir": "build"
            }
        }

        site_data = await self._make_request_with_retry(
            'POST',
            f"{NETLIFY_API}/sites",
            headers=headers,
            json_data=payload
        )

        self.logger.info(f"Created new Netlify site: {site_name}")
        return site_data

    def _get_build_settings(self, project_config: Dict[str, Any]) -> Dict[str, Any]:
        """Get build settings from project configuration"""

        # Default build settings
        build_settings = {
            "build_command": project_config.get("build_command", "npm run build"),
            "publish_dir": project_config.get("output_directory", "build"),
            "repo_branch": "main"
        }

        # Framework-specific overrides
        framework = project_config.get('framework', '').lower()
        project_type = project_config.get('project_type', '').lower()

        if framework == 'nextjs' or project_type == 'next':
            build_settings.update({
                "build_command": "npm run build",
                "publish_dir": ".next"
            })
        elif framework == 'react' or project_type == 'react':
            build_settings.update({
                "build_command": "npm run build",
                "publish_dir": "build"
            })
        elif framework == 'vue' or project_type == 'vue':
            build_settings.update({
                "build_command": "npm run build",
                "publish_dir": "dist"
            })

        return build_settings

    async def _configure_site_build_settings(self, headers: Dict[str, str], site_id: str, build_settings: Dict[str, Any]):
        """Configure build settings for the site"""

        try:
            await self._make_request_with_retry(
                'PATCH',
                f"{NETLIFY_API}/sites/{site_id}",
                headers=headers,
                json_data={"build_settings": build_settings}
            )
            self.logger.debug(f"Updated build settings for site: {site_id}")
        except DeploymentError as e:
            self.logger.warning(f"Could not update build settings: {e.message}")
            # Continue anyway - build settings can be updated during deployment

    async def _trigger_deployment(self, headers: Dict[str, str], site: Dict[str, Any], repo_url: str) -> Dict[str, Any]:
        """Trigger a new deployment"""

        payload = {
            "repository": {
                "provider": "github",
                "repo": repo_url.replace("https://github.com/", ""),
                "branch": "main",
                "private": False
            },
            "clear_cache": True
        }

        return await self._make_request_with_retry(
            'POST',
            f"{NETLIFY_API}/sites/{site['id']}/deploys",
            headers=headers,
            json_data=payload
        )

# Legacy function for backward compatibility
async def deploy(project_path: str, project_config: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy deployment function - use NetlifyAdapter for new code"""
    adapter = NetlifyAdapter()
    result = await adapter.deploy(project_path, project_config, env)

    # Convert to legacy format for backward compatibility
    return {
        "status": result.status,
        "deployment_id": result.deployment_id,
        "url": result.url,
        "deploy_ssl_url": result.url,  # Netlify SSL URL is the same as main URL
        "platform": result.platform,
        "error": result.error_message,
        **result.metadata
    }
