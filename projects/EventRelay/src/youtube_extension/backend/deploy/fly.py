#!/usr/bin/env python3
"""
Fly.io deployment adapter for UVAI platform.
Updated to use new base adapter architecture with retry logic and proper error handling.
"""

import os
import asyncio
import subprocess
from typing import Dict, Any, Optional, List
from pathlib import Path
from .core import BaseDeploymentAdapter, DeploymentResult, EnvironmentValidator, DeploymentError

class FlyAdapter(BaseDeploymentAdapter):
    """Fly.io deployment adapter with enhanced error handling and monitoring"""

    def __init__(self):
        super().__init__('fly')

    async def _deploy_impl(self, project_path: str, project_config: Dict[str, Any], env: Dict[str, Any]) -> DeploymentResult:
        """Fly.io-specific deployment implementation"""

        # Get Fly token
        token = EnvironmentValidator.get_token('FLY_API_TOKEN')
        if not token:
            raise DeploymentError(
                platform=self.platform,
                operation='validation',
                message="FLY_API_TOKEN not configured"
            )

        # Check if flyctl is installed
        if not await self._is_flyctl_installed():
            raise DeploymentError(
                platform=self.platform,
                operation='validation',
                message="flyctl not installed or not in PATH"
            )

        # Create fly.toml if it doesn't exist
        await self._ensure_fly_config(project_path, project_config, env)

        # Set environment variables for flyctl
        env_vars = os.environ.copy()
        env_vars["FLY_API_TOKEN"] = token

        # Launch deployment
        self.logger.info("Starting Fly.io deployment...")
        deploy_result = await self._run_flyctl_deploy(project_path, env_vars)

        # Parse deployment URL from output
        deployment_url = self._extract_deployment_url(deploy_result['output'])

        # Extract app name and deployment details
        app_name = env.get("FLY_APP_NAME") or self._generate_app_name(project_config)

        return DeploymentResult(
            status='success',
            platform=self.platform,
            deployment_id=f"fly-{app_name}-{int(asyncio.get_event_loop().time())}",
            url=deployment_url,
            build_log_url=f"https://fly.io/apps/{app_name}",
            metadata={
                'app_name': app_name,
                'deploy_output': deploy_result['output'],
                'exit_code': deploy_result['exit_code']
            }
        )

    async def _is_flyctl_installed(self) -> bool:
        """Check if flyctl is installed and accessible"""
        try:
            result = await self._run_flyctl_command(["flyctl", "version"])
            return result['exit_code'] == 0
        except Exception:
            return False

    async def _run_flyctl_command(self, args: List[str], env_vars: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Run a flyctl command with proper error handling"""
        try:
            env = env_vars or os.environ.copy()
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            stdout, stderr = await proc.communicate()

            output = stdout.decode()
            error_output = stderr.decode()

            if proc.returncode != 0:
                raise DeploymentError(
                    platform=self.platform,
                    operation='flyctl_command',
                    message=f"flyctl command failed: {error_output}",
                    details={
                        'command': args,
                        'exit_code': proc.returncode,
                        'stdout': output,
                        'stderr': error_output
                    }
                )

            return {
                'exit_code': proc.returncode,
                'output': output,
                'error_output': error_output
            }

        except asyncio.TimeoutError:
            raise DeploymentError(
                platform=self.platform,
                operation='flyctl_command',
                message="flyctl command timed out",
                recoverable=True
            )

    async def _run_flyctl_deploy(self, project_path: str, env_vars: Dict[str, str]) -> Dict[str, Any]:
        """Run flyctl deploy command"""
        deploy_args = [
            "flyctl", "deploy",
            "--remote-only",  # Don't use local docker
            "--yes"  # Auto-confirm prompts
        ]

        # Add project path if specified
        if project_path and Path(project_path).exists():
            deploy_args.append(project_path)

        return await self._run_flyctl_command(deploy_args, env_vars)

    async def _ensure_fly_config(self, project_path: str, project_config: Dict[str, Any], env: Dict[str, Any]):
        """Ensure fly.toml configuration exists"""
        fly_config_path = Path(project_path) / "fly.toml"

        if fly_config_path.exists():
            self.logger.info("fly.toml already exists, using existing configuration")
            return

        # Generate fly.toml content
        app_name = env.get("FLY_APP_NAME") or self._generate_app_name(project_config)

        fly_config = f"""\
app = "{app_name}"
primary_region = "iad"

[build]
  builder = "paketobuildpacks/builder:base"
  buildpacks = ["gcr.io/paketo-buildpacks/nodejs"]

[env]
  NODE_ENV = "production"

[[services]]
  internal_port = 3000
  protocol = "tcp"

  [[services.ports]]
    handlers = ["http"]
    port = "80"

  [[services.ports]]
    handlers = ["tls", "http"]
    port = "443"
"""

        # Write fly.toml
        with open(fly_config_path, 'w') as f:
            f.write(fly_config)

        self.logger.info(f"Created fly.toml for app: {app_name}")

    def _generate_app_name(self, project_config: Dict[str, Any]) -> str:
        """Generate a unique app name for Fly.io"""
        title = project_config.get('title', 'uvai-app')
        sanitized = ''.join(c for c in title.lower().replace(' ', '-') if c.isalnum() or c == '-')
        timestamp = int(asyncio.get_event_loop().time()) % 10000
        return f"uvai-{sanitized[:20]}-{timestamp}"

    def _extract_deployment_url(self, output: str) -> Optional[str]:
        """Extract deployment URL from flyctl output"""
        lines = output.splitlines()
        for line in lines:
            line = line.strip()
            if "https://" in line and ".fly.dev" in line:
                return line

        # Fallback patterns
        for line in lines:
            if "==> Monitoring deployment" in line:
                # Try to extract URL from subsequent lines
                continue
            if "https://" in line and any(domain in line for domain in [".fly.dev", ".internal"]):
                return line

        # Return a placeholder URL if we can't extract the real one
        return "https://deployment-in-progress.fly.dev"

# Legacy function for backward compatibility
async def deploy(project_path: str, project_config: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy deployment function - use FlyAdapter for new code"""
    adapter = FlyAdapter()
    result = await adapter.deploy(project_path, project_config, env)

    # Convert to legacy format for backward compatibility
    return {
        "status": result.status,
        "url": result.url,
        "raw_output": result.metadata.get('deploy_output', ''),
        "platform": result.platform,
        "error": result.error_message,
        **result.metadata
    }

# Keep the old helper function for internal use
async def _run_flyctl(args):
    """Legacy helper function for backward compatibility"""
    import warnings
    warnings.warn("_run_flyctl is deprecated, use FlyAdapter instead", DeprecationWarning, stacklevel=2)

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return proc.returncode, stdout.decode(), stderr.decode()
    except Exception as e:
        return -1, "", str(e)
