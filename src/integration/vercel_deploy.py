"""
Vercel CLI - Automated Deployment
----------------------------------
Deploy generated apps to Vercel with automatic configuration.
"""

import os
import asyncio
import json
import httpx
from typing import Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DeploymentResult:
    """Result from Vercel deployment."""
    deployment_id: str
    url: str
    preview_url: str
    state: str
    created_at: str
    project_name: str


@dataclass
class ProjectConfig:
    """Vercel project configuration."""
    name: str
    framework: str = "nextjs"
    build_command: Optional[str] = None
    output_directory: Optional[str] = None
    env_vars: Optional[dict] = None


class VercelDeployService:
    """Vercel deployment service using REST API and CLI."""
    
    API_BASE = "https://api.vercel.com"
    
    def __init__(self, token: Optional[str] = None, team_id: Optional[str] = None):
        self.token = token or os.environ.get("VERCEL_TOKEN")
        if not self.token:
            raise ValueError("VERCEL_TOKEN required")
        self.team_id = team_id or os.environ.get("VERCEL_TEAM_ID")
        self.client = httpx.AsyncClient(
            timeout=120.0,
            headers={"Authorization": f"Bearer {self.token}"}
        )
    
    async def deploy_directory(
        self,
        source_dir: str,
        project_name: str,
        production: bool = False
    ) -> DeploymentResult:
        """Deploy a local directory to Vercel using CLI."""
        
        cmd = ["vercel", "--yes", "--token", self.token]
        if production:
            cmd.append("--prod")
        if project_name:
            cmd.extend(["--name", project_name])
        if self.team_id:
            cmd.extend(["--scope", self.team_id])
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=source_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Vercel deploy failed: {stderr.decode()}")
        
        url = stdout.decode().strip().split("\n")[-1]
        
        return DeploymentResult(
            deployment_id=url.split("/")[-1],
            url=url,
            preview_url=url,
            state="READY",
            created_at="",
            project_name=project_name
        )
    
    async def deploy_from_github(
        self,
        repo: str,
        branch: str = "main",
        project_name: Optional[str] = None
    ) -> DeploymentResult:
        """Deploy directly from a GitHub repository."""
        
        payload = {
            "name": project_name or repo.split("/")[-1],
            "gitSource": {
                "type": "github",
                "repo": repo,
                "ref": branch
            }
        }
        
        params = {}
        if self.team_id:
            params["teamId"] = self.team_id
        
        response = await self.client.post(
            f"{self.API_BASE}/v13/deployments",
            params=params,
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        
        return DeploymentResult(
            deployment_id=data["id"],
            url=f"https://{data['url']}",
            preview_url=f"https://{data['url']}",
            state=data["readyState"],
            created_at=data["createdAt"],
            project_name=data["name"]
        )
    
    async def get_deployment_status(self, deployment_id: str) -> dict:
        """Check deployment status."""
        
        params = {}
        if self.team_id:
            params["teamId"] = self.team_id
        
        response = await self.client.get(
            f"{self.API_BASE}/v13/deployments/{deployment_id}",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    async def list_projects(self) -> list[dict]:
        """List all Vercel projects."""
        
        params = {"limit": 100}
        if self.team_id:
            params["teamId"] = self.team_id
        
        response = await self.client.get(
            f"{self.API_BASE}/v9/projects",
            params=params
        )
        response.raise_for_status()
        return response.json().get("projects", [])
    
    async def create_project(self, config: ProjectConfig) -> dict:
        """Create a new Vercel project."""
        
        payload = {
            "name": config.name,
            "framework": config.framework,
        }
        if config.build_command:
            payload["buildCommand"] = config.build_command
        if config.output_directory:
            payload["outputDirectory"] = config.output_directory
        
        params = {}
        if self.team_id:
            params["teamId"] = self.team_id
        
        response = await self.client.post(
            f"{self.API_BASE}/v10/projects",
            params=params,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def set_env_vars(
        self,
        project_id: str,
        env_vars: dict[str, str],
        target: list[str] = ["production", "preview", "development"]
    ) -> list[dict]:
        """Set environment variables for a project."""
        
        results = []
        for key, value in env_vars.items():
            payload = {
                "key": key,
                "value": value,
                "type": "encrypted",
                "target": target
            }
            
            params = {}
            if self.team_id:
                params["teamId"] = self.team_id
            
            response = await self.client.post(
                f"{self.API_BASE}/v10/projects/{project_id}/env",
                params=params,
                json=payload
            )
            if response.status_code == 200:
                results.append(response.json())
        
        return results
    
    async def delete_deployment(self, deployment_id: str) -> bool:
        """Delete a deployment."""
        
        params = {}
        if self.team_id:
            params["teamId"] = self.team_id
        
        response = await self.client.delete(
            f"{self.API_BASE}/v13/deployments/{deployment_id}",
            params=params
        )
        return response.status_code == 200
    
    @staticmethod
    def generate_vercel_json(
        framework: str = "nextjs",
        routes: Optional[list] = None
    ) -> dict:
        """Generate vercel.json configuration."""
        
        config = {"version": 2}
        
        if framework == "nextjs":
            config["framework"] = "nextjs"
        elif framework == "react":
            config["builds"] = [{"src": "package.json", "use": "@vercel/static-build"}]
        
        if routes:
            config["routes"] = routes
        
        return config
    
    async def close(self):
        await self.client.aclose()
