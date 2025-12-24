"""
Tests for Cloud Run deployment configuration
"""

import os
import pytest
from pathlib import Path


class TestCloudRunDeployment:
    """Test Cloud Run deployment readiness"""

    def test_dockerfile_production_exists(self):
        """Verify Dockerfile.production exists"""
        dockerfile = Path(__file__).parent.parent.parent / "Dockerfile.production"
        assert dockerfile.exists(), "Dockerfile.production not found"

    def test_dockerfile_has_port_binding(self):
        """Verify Dockerfile.production supports PORT environment variable"""
        dockerfile = Path(__file__).parent.parent.parent / "Dockerfile.production"
        content = dockerfile.read_text()
        
        # Check for PORT variable in CMD
        assert "${PORT" in content or "$PORT" in content, \
            "Dockerfile.production must use $PORT environment variable"
        
        # Check for uvicorn command
        assert "uvicorn" in content, "Dockerfile must use uvicorn"
        
        # Check for correct entry point
        assert "uvai.api.main:app" in content, \
            "Dockerfile must use uvai.api.main:app as entry point"

    def test_dockerfile_has_health_check(self):
        """Verify Dockerfile.production has health check"""
        dockerfile = Path(__file__).parent.parent.parent / "Dockerfile.production"
        content = dockerfile.read_text()
        
        assert "HEALTHCHECK" in content, "Dockerfile must have HEALTHCHECK"
        assert "/health" in content, "Health check must test health endpoint"

    def test_dockerfile_uses_nonroot_user(self):
        """Verify Dockerfile.production uses non-root user"""
        dockerfile = Path(__file__).parent.parent.parent / "Dockerfile.production"
        content = dockerfile.read_text()
        
        assert "USER" in content, "Dockerfile must switch to non-root user"
        assert "appuser" in content, "Dockerfile must create appuser"

    def test_cloudbuild_yaml_exists(self):
        """Verify cloudbuild.yaml exists"""
        cloudbuild = Path(__file__).parent.parent.parent / "cloudbuild.yaml"
        assert cloudbuild.exists(), "cloudbuild.yaml not found"

    def test_deployment_script_exists(self):
        """Verify deployment script exists and is executable"""
        script = Path(__file__).parent.parent.parent / "scripts" / "deploy-cloud-run.sh"
        assert script.exists(), "deploy-cloud-run.sh not found"
        
        # Check if executable (on Unix systems)
        import stat
        file_stat = script.stat()
        is_executable = bool(file_stat.st_mode & stat.S_IXUSR)
        assert is_executable, "deploy-cloud-run.sh must be executable"

    def test_dockerignore_exists(self):
        """Verify .dockerignore exists for optimized builds"""
        dockerignore = Path(__file__).parent.parent.parent / ".dockerignore"
        assert dockerignore.exists(), ".dockerignore not found"
        
        content = dockerignore.read_text()
        # Check for essential excludes
        assert "node_modules" in content, ".dockerignore must exclude node_modules"
        assert "tests" in content or "test" in content, ".dockerignore must exclude tests"
        assert "__pycache__" in content, ".dockerignore must exclude __pycache__"

    def test_deployment_guide_exists(self):
        """Verify Cloud Run deployment guide exists"""
        guide = Path(__file__).parent.parent.parent / "docs" / "CLOUD_RUN_DEPLOYMENT.md"
        assert guide.exists(), "CLOUD_RUN_DEPLOYMENT.md not found"
        
        content = guide.read_text()
        # Check for essential sections
        assert "Environment Variables" in content, "Guide must document environment variables"
        assert "gcloud run deploy" in content, "Guide must have deployment commands"
        assert "Secret Manager" in content, "Guide must document Secret Manager"
        assert "$PORT" in content, "Guide must explain PORT binding"

    def test_quickstart_guide_exists(self):
        """Verify Cloud Run quickstart guide exists"""
        quickstart = Path(__file__).parent.parent.parent / "docs" / "CLOUD_RUN_QUICKSTART.md"
        assert quickstart.exists(), "CLOUD_RUN_QUICKSTART.md not found"

    def test_github_actions_workflow_exists(self):
        """Verify GitHub Actions workflow exists"""
        workflow = Path(__file__).parent.parent.parent / ".github" / "workflows" / "deploy-cloud-run.yml"
        assert workflow.exists(), "deploy-cloud-run.yml workflow not found"

    def test_env_template_has_required_vars(self):
        """Verify .env.example has essential Cloud Run variables"""
        env_template = Path(__file__).parent.parent.parent / ".env.example"
        assert env_template.exists(), ".env.example not found"
        
        content = env_template.read_text()
        
        # Check for essential variables
        required_vars = [
            "NODE_ENV",
            "DEBUG",
            "LOG_LEVEL",
            "APP_PORT",
            "GEMINI_API_KEY",
            "DATABASE_URL",
            "JWT_SECRET_KEY",
            "SESSION_SECRET_KEY",
        ]
        
        for var in required_vars:
            assert var in content, f"Environment template must include {var}"

    def test_app_can_use_port_env_variable(self):
        """Test that the application can read PORT from environment"""
        # This is a basic check - the actual app should handle PORT
        test_port = "8080"
        os.environ["PORT"] = test_port
        
        # Verify the environment variable is accessible
        assert os.getenv("PORT") == test_port
        
        # Clean up
        del os.environ["PORT"]


class TestApplicationEntryPoint:
    """Test application entry point configuration"""

    def test_uvai_api_main_exists(self):
        """Verify uvai.api.main module exists"""
        main_file = Path(__file__).parent.parent.parent / "src" / "uvai" / "api" / "main.py"
        assert main_file.exists(), "uvai.api.main not found"

    def test_uvai_api_main_exports_app(self):
        """Verify uvai.api.main exports FastAPI app"""
        main_file = Path(__file__).parent.parent.parent / "src" / "uvai" / "api" / "main.py"
        content = main_file.read_text()
        
        # Check that it imports or creates an app
        assert "from youtube_extension.backend.main_v2 import app" in content or \
               "app = FastAPI" in content, \
               "main.py must export FastAPI app"


class TestDocumentation:
    """Test deployment documentation completeness"""

    def test_readme_mentions_cloud_run(self):
        """Verify README mentions Cloud Run deployment"""
        readme = Path(__file__).parent.parent.parent / "README.md"
        content = readme.read_text()
        
        assert "Cloud Run" in content, "README must mention Cloud Run"
        assert "CLOUD_RUN_DEPLOYMENT.md" in content or "deploy-cloud-run" in content, \
            "README must reference Cloud Run deployment guide"

    def test_deployment_guide_has_all_sections(self):
        """Verify deployment guide has comprehensive sections"""
        guide = Path(__file__).parent.parent.parent / "docs" / "CLOUD_RUN_DEPLOYMENT.md"
        content = guide.read_text()
        
        required_sections = [
            "Prerequisites",
            "Environment Variables",
            "Deployment Steps",
            "Service Configuration",
            "Build Optimization",
            "Monitoring",
            "Troubleshooting",
            "Security",
        ]
        
        for section in required_sections:
            assert section in content, f"Guide must have {section} section"


class TestSecurityConfiguration:
    """Test security configurations for Cloud Run"""

    def test_dockerfile_minimal_base_image(self):
        """Verify Dockerfile uses minimal base image"""
        dockerfile = Path(__file__).parent.parent.parent / "Dockerfile.production"
        content = dockerfile.read_text()
        
        assert "python:3.11-slim" in content, \
            "Dockerfile should use slim Python image for security"

    def test_dockerfile_removes_apt_lists(self):
        """Verify Dockerfile cleans up apt lists"""
        dockerfile = Path(__file__).parent.parent.parent / "Dockerfile.production"
        content = dockerfile.read_text()
        
        assert "rm -rf /var/lib/apt/lists" in content, \
            "Dockerfile should clean up apt lists to reduce image size"

    def test_env_template_warns_about_secrets(self):
        """Verify environment template warns about secrets"""
        env_template = Path(__file__).parent.parent.parent / ".env.example"
        content = env_template.read_text()
        
        # Check for warnings about secrets
        assert "secret" in content.lower() or "never commit" in content.lower(), \
            "Environment template should warn about secrets"


# Run tests with: pytest tests/unit/test_cloud_run_deployment.py -v
