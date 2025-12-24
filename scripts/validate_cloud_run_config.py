#!/usr/bin/env python3
"""
Validate Cloud Run deployment configuration

This script validates that all necessary files and configurations are present
for deploying EventRelay to Google Cloud Run.

Usage:
    python scripts/validate_cloud_run_config.py
"""

import sys
from pathlib import Path
from typing import List, Tuple

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def check_file_exists(filepath: Path, description: str) -> bool:
    """Check if a file exists"""
    if filepath.exists():
        print(f"{GREEN}✓{RESET} {description}: {filepath.name}")
        return True
    else:
        print(f"{RED}✗{RESET} {description}: {filepath.name} NOT FOUND")
        return False


def check_file_content(filepath: Path, required_strings: List[str], description: str) -> Tuple[bool, List[str]]:
    """Check if file contains required strings"""
    if not filepath.exists():
        return False, [f"File not found: {filepath}"]
    
    content = filepath.read_text()
    missing = []
    
    for req in required_strings:
        if req not in content:
            missing.append(req)
    
    if not missing:
        print(f"{GREEN}✓{RESET} {description}")
        return True, []
    else:
        print(f"{RED}✗{RESET} {description}")
        for item in missing:
            print(f"  {YELLOW}Missing:{RESET} {item}")
        return False, missing


def main():
    """Main validation function"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}EventRelay Cloud Run Deployment Configuration Validator{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    all_checks_passed = True
    
    # Check 1: Essential files exist
    print(f"\n{BLUE}[1] Checking Essential Files{RESET}")
    print("-" * 60)
    
    essential_files = [
        (project_root / "Dockerfile.production", "Production Dockerfile"),
        (project_root / "cloudbuild.yaml", "Cloud Build config"),
        (project_root / "scripts" / "deploy-cloud-run.sh", "Deployment script"),
        (project_root / ".dockerignore", "Docker ignore file"),
        (project_root / "docs" / "CLOUD_RUN_DEPLOYMENT.md", "Deployment guide"),
        (project_root / "docs" / "CLOUD_RUN_QUICKSTART.md", "Quick start guide"),
        (project_root / ".env.production.template", "Environment template"),
        (project_root / ".github" / "workflows" / "deploy-cloud-run.yml", "GitHub Actions workflow"),
    ]
    
    for filepath, description in essential_files:
        if not check_file_exists(filepath, description):
            all_checks_passed = False
    
    # Check 2: Dockerfile.production configuration
    print(f"\n{BLUE}[2] Checking Dockerfile.production{RESET}")
    print("-" * 60)
    
    dockerfile = project_root / "Dockerfile.production"
    dockerfile_checks = [
        "${PORT",  # PORT environment variable support
        "uvicorn",  # Uses uvicorn
        "uvai.api.main:app",  # Correct entry point
        "HEALTHCHECK",  # Health check configured
        "USER appuser",  # Non-root user
        "python:3.11-slim",  # Minimal base image
    ]
    
    passed, _ = check_file_content(
        dockerfile,
        dockerfile_checks,
        "Dockerfile.production has required configuration"
    )
    if not passed:
        all_checks_passed = False
    
    # Check 3: Cloud Build configuration
    print(f"\n{BLUE}[3] Checking cloudbuild.yaml{RESET}")
    print("-" * 60)
    
    cloudbuild = project_root / "cloudbuild.yaml"
    cloudbuild_checks = [
        "gcr.io/cloud-builders/docker",  # Docker builder
        "entrypoint: gcloud",  # Cloud Run deployment
        "Dockerfile.production",  # Uses production Dockerfile
    ]
    
    passed, _ = check_file_content(
        cloudbuild,
        cloudbuild_checks,
        "cloudbuild.yaml has required steps"
    )
    if not passed:
        all_checks_passed = False
    
    # Check 4: Environment variables
    print(f"\n{BLUE}[4] Checking Environment Variables{RESET}")
    print("-" * 60)
    
    env_template = project_root / ".env.production.template"
    env_vars = [
        "ENVIRONMENT",
        "DEBUG",
        "LOG_LEVEL",
        "APP_PORT",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "DATABASE_URL",
        "JWT_SECRET_KEY",
        "SESSION_SECRET_KEY",
    ]
    
    passed, _ = check_file_content(
        env_template,
        env_vars,
        "Environment template has required variables"
    )
    if not passed:
        all_checks_passed = False
    
    # Check 5: Documentation
    print(f"\n{BLUE}[5] Checking Documentation{RESET}")
    print("-" * 60)
    
    deployment_guide = project_root / "docs" / "CLOUD_RUN_DEPLOYMENT.md"
    doc_sections = [
        "Prerequisites",
        "Environment Variables",
        "Deployment Steps",
        "gcloud run deploy",
        "Service Configuration",
        "Build Optimization",
        "Monitoring",
        "Troubleshooting",
    ]
    
    passed, _ = check_file_content(
        deployment_guide,
        doc_sections,
        "Deployment guide has comprehensive sections"
    )
    if not passed:
        all_checks_passed = False
    
    # Check 6: Application entry point
    print(f"\n{BLUE}[6] Checking Application Entry Point{RESET}")
    print("-" * 60)
    
    main_file = project_root / "src" / "uvai" / "api" / "main.py"
    if check_file_exists(main_file, "Application entry point (uvai.api.main)"):
        # Check that it exports app
        content = main_file.read_text()
        if "app" in content:
            print(f"{GREEN}✓{RESET} Entry point exports 'app' object")
        else:
            print(f"{RED}✗{RESET} Entry point should export 'app' object")
            all_checks_passed = False
    else:
        all_checks_passed = False
    
    # Check 7: Security configurations
    print(f"\n{BLUE}[7] Checking Security Configurations{RESET}")
    print("-" * 60)
    
    dockerignore = project_root / ".dockerignore"
    security_excludes = [
        ".env",
        "*.log",
        "tests",
        "__pycache__",
    ]
    
    passed, _ = check_file_content(
        dockerignore,
        security_excludes,
        ".dockerignore excludes sensitive files"
    )
    if not passed:
        all_checks_passed = False
    
    # Check 8: Deployment script is executable
    print(f"\n{BLUE}[8] Checking Deployment Script Permissions{RESET}")
    print("-" * 60)
    
    deploy_script = project_root / "scripts" / "deploy-cloud-run.sh"
    if deploy_script.exists():
        import stat
        file_stat = deploy_script.stat()
        is_executable = bool(file_stat.st_mode & stat.S_IXUSR)
        
        if is_executable:
            print(f"{GREEN}✓{RESET} deploy-cloud-run.sh is executable")
        else:
            print(f"{YELLOW}⚠{RESET} deploy-cloud-run.sh is not executable")
            print(f"  Run: chmod +x {deploy_script}")
    
    # Final summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    if all_checks_passed:
        print(f"{GREEN}✓ All checks passed! Configuration is ready for Cloud Run deployment.{RESET}")
        print(f"\n{BLUE}Next steps:{RESET}")
        print(f"  1. Set up Google Cloud project and enable APIs")
        print(f"  2. Create Secret Manager secrets for API keys")
        print(f"  3. Run: ./scripts/deploy-cloud-run.sh production --project your-project-id")
        print(f"  4. Or use: gcloud run deploy eventrelay-api --source . --region us-central1")
        print(f"\n{BLUE}Documentation:{RESET}")
        print(f"  • Full guide: docs/CLOUD_RUN_DEPLOYMENT.md")
        print(f"  • Quick start: docs/CLOUD_RUN_QUICKSTART.md")
        return 0
    else:
        print(f"{RED}✗ Some checks failed. Please fix the issues above.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
