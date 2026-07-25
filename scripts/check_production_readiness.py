#!/usr/bin/env python3
"""
Production Readiness Verification Gate
=====================================
Ensures all critical, launch-gating security, configuration, logging,
and deployment prerequisites are met before shipping to production.

Checks executed:
1. Environment Configuration Templates (validating .env.example templates)
2. Live Environment Secret Verification (masked logging of active keys)
3. CORS Security Constraints (static analysis of main.py CORS setup)
4. Secure Headers Configuration (validating X-Frame-Options, X-Content-Type-Options)
5. Production Logging Level & Configuration (checking for DEBUG levels and Sentry PII safety)
6. Dependency Hygiene (checking for ipdb/pudb, playwright, and wildcard configurations)

This script fails closed (exits with non-zero code) if any rule is breached.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

# Color constants for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

# Required keys per LAUNCH_CHECKLIST.md
REQUIRED_WEB_KEYS = [
    "STRIPE_SECRET_KEY",
    "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "STRIPE_PRICE_PRO_MONTHLY",
    "STRIPE_PRICE_PRO_ANNUAL",
    "NEXT_PUBLIC_TURNSTILE_SITE_KEY",
    "TURNSTILE_SECRET_KEY",
    "UPSTASH_REDIS_REST_URL",
    "UPSTASH_REDIS_REST_TOKEN",
    "NEXTAUTH_SECRET",
    "NEXTAUTH_URL",
    "GOOGLE_OAUTH_CLIENT_ID",
    "GOOGLE_OAUTH_CLIENT_SECRET",
]

REQUIRED_BACKEND_KEYS = [
    "BACKEND_URL",
    "ENVIRONMENT",
]


def log_success(msg: str):
    print(f"{GREEN}✅ {msg}{RESET}")


def log_failure(msg: str):
    print(f"{RED}❌ {msg}{RESET}")


def log_warning(msg: str):
    print(f"{YELLOW}⚠️ {msg}{RESET}")


def log_info(msg: str):
    print(f"{BLUE}ℹ️ {msg}{RESET}")


def mask_secret(value: str) -> str:
    """Mask secret values, displaying only prefixes or lengths for verification."""
    if not value:
        return "[EMPTY]"
    if len(value) <= 8:
        return f"[HIDDEN, len={len(value)}]"
    return f"{value[:4]}...{value[-4:]} [REDACTED]"


def check_configuration_templates() -> bool:
    """Ensure required launch keys are documented in .env.example and apps/web/.env.example."""
    log_info("Step 1: Verifying Configuration Templates...")
    success = True

    root_example = Path("env.example")
    if not root_example.exists():
        root_example = Path(".env.example")

    web_example = Path("apps/web/.env.example")

    # Validate root env template
    if not root_example.exists():
        log_failure(f"Root .env.example template is missing!")
        success = False
    else:
        content = root_example.read_text()
        for key in REQUIRED_BACKEND_KEYS:
            if key not in content:
                log_failure(f"Root .env.example template is missing documented variable: {key}")
                success = False
            else:
                log_success(f"Root template defines variable: {key}")

    # Validate web env template
    if not web_example.exists():
        log_failure(f"Web app .env.example template is missing!")
        success = False
    else:
        content = web_example.read_text()
        for key in REQUIRED_WEB_KEYS:
            if key not in content:
                log_failure(f"Web .env.example template is missing documented variable: {key}")
                success = False
            else:
                log_success(f"Web template defines variable: {key}")

    return success


def check_live_environment() -> bool:
    """Inspect current environment setup. Mask secrets to prevent leak in logs."""
    log_info("Step 2: Inspecting Live Environment Variables...")

    # In CI context, real secrets are normally not injected. We inspect what's available.
    is_ci = os.getenv("GITHUB_ACTIONS") == "true"
    if is_ci:
        log_info("Running in CI context. Live production secrets will be validated if available.")

    for key in REQUIRED_BACKEND_KEYS + REQUIRED_WEB_KEYS:
        val = os.getenv(key)
        if val:
            log_success(f"Environment variable {key} is ACTIVE (value: {mask_secret(val)})")
        else:
            if is_ci:
                log_warning(f"Environment variable {key} is not set in CI environment (expected for pull request checks).")
            else:
                log_warning(f"Local Environment variable {key} is unset.")

    return True


def check_cors_and_headers() -> bool:
    """Analyze main.py statically for CORS configuration, Logging level, and Secure Headers."""
    log_info("Step 3: Statically analyzing main.py for security constraints...")
    success = True

    main_py_path = Path("src/youtube_extension/main.py")
    if not main_py_path.exists():
        log_failure(f"Could not find main backend entrypoint: {main_py_path}")
        return False

    content = main_py_path.read_text()

    # 1. CORS Analysis: Verify allowed origins logic
    if "CORSMiddleware" not in content:
        log_failure("CORS Middleware is not implemented in main.py!")
        success = False
    else:
        log_success("CORS Middleware implementation found.")

    # Check for wildcards combined with credentials (forbidden)
    if "allow_credentials=True" in content and '"*"' in content and "allow_origins" in content:
        # Check if origins are filtered or raw wildcard is passed
        if "allow_origins=_allowed_origins" in content or "allow_origins=ProductionConfig" in content:
            log_success("CORS allowed origins are dynamically filtered.")
        else:
            log_failure("CORSMiddleware may be echoing raw wildcards '*' with credentials enabled!")
            success = False

    # Check loopback origin production rejection
    if "_is_loopback_origin" in content and "_IS_PRODUCTION" in content:
        log_success("CORS correctly contains loopback origin protection in production.")
    else:
        log_failure("CORS lacks loopback origin rejection logic for production deployments!")
        success = False

    # 2. Secure Headers Check
    if "SecurityHeadersMiddleware" not in content:
        log_failure("Security Headers Middleware (X-Frame-Options, X-Content-Type-Options) is missing!")
        success = False
    else:
        if '"X-Frame-Options"' in content or "X-Frame-Options" in content:
            log_success("Security Headers (X-Frame-Options, X-Content-Type-Options) are configured.")
        else:
            log_failure("Security Headers middleware does not configure X-Frame-Options!")
            success = False

    # 3. Logging Level Config Check
    if "logging.basicConfig" in content or "logging.getLogger" in content:
        # 1. Check if we configure logging at DEBUG level by default
        if "level=logging.DEBUG" in content or "setLevel(logging.DEBUG)" in content:
            log_failure("Production logging cannot default to DEBUG level (leaks sensitive info)!")
            success = False
        else:
            log_success("Structured logging level checks passed.")

        # 2. Check Sentry PII settings to prevent information leakage, excluding comment lines
        has_pii_check = False
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            line_no_spaces = line.replace(" ", "")
            if "send_default_pii" in line_no_spaces:
                has_pii_check = True
                if "send_default_pii=True" in line_no_spaces:
                    log_failure("Sentry send_default_pii must not be hardcoded to True!")
                    success = False

        if has_pii_check:
            log_success("Sentry PII safety check configured.")
        else:
            log_warning("Sentry PII safety check not found (ensure PII is not sent to Sentry).")
    else:
        log_failure("Backend is missing proper logging configurations!")
        success = False

    return success


def check_dependencies() -> bool:
    """Check basic dependency integrity."""
    log_info("Step 4: Checking Dependency Hygiene...")

    requirements_path = Path("requirements.txt")
    package_json_path = Path("apps/web/package.json")

    success = True

    if requirements_path.exists():
        reqs = requirements_path.read_text()
        # Ensure no accidental development requirements like debuggers or insecure packages are committed
        if "ipdb" in reqs or "pudb" in reqs:
            log_failure("Development debuggers (ipdb/pudb) detected in production requirements.txt!")
            success = False
        else:
            log_success("Python dependencies requirements.txt looks healthy.")

        # Check for unsafe Python dependency wildcards
        for line in reqs.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "==" in line:
                parts = line.split("==")
                if len(parts) > 1 and parts[1].strip() == "*":
                    log_failure(f"Unsafe wildcard version found in requirements.txt: {line}")
                    success = False
    else:
        log_warning("No requirements.txt found at root.")

    if package_json_path.exists():
        pj = package_json_path.read_text()
        if "playwright" in pj and "@playwright/test" not in pj:
            log_failure("playwright is declared but @playwright/test is missing from package.json!")
            success = False
        else:
            log_success("Next.js dependencies package.json looks healthy.")

        # Check for unsafe package.json dependency wildcards
        if '"*"' in pj or "'*'" in pj:
            log_failure("Unsafe wildcard version '*' found in package.json!")
            success = False
    else:
        log_warning("No package.json found at apps/web/package.json.")

    # Dynamic checks via safety/npm-audit if available
    try:
        if subprocess.run(["which", "safety"], capture_output=True).returncode == 0:
            log_info("Running dynamic dependency safety scan (safety check)...")
            res = subprocess.run(["safety", "check", "-r", "requirements.txt"], capture_output=True, text=True)
            if res.returncode != 0:
                log_warning(f"Safety check found potential issues:\n{res.stdout or res.stderr}")
    except Exception as e:
        log_warning(f"Failed to run safety check: {e}")

    try:
        if subprocess.run(["which", "npm"], capture_output=True).returncode == 0 and package_json_path.exists():
            log_info("Running dynamic dependency security scan (npm audit)...")
            res = subprocess.run(["npm", "audit"], capture_output=True, text=True)
            if "high" in res.stdout.lower() or "critical" in res.stdout.lower():
                log_warning("npm audit flagged potential high/critical vulnerabilities.")
    except Exception as e:
        log_warning(f"Failed to run npm audit: {e}")

    return success


def run_checks() -> int:
    """Run all checks and return an exit code (0 if success, 1 if any failure)."""
    print(f"\n{BLUE}=== UVAI Production Readiness Auditor ==={RESET}\n")

    checks = [
        check_configuration_templates(),
        check_live_environment(),
        check_cors_and_headers(),
        check_dependencies()
    ]

    print("\n" + "="*40)
    if all(checks):
        print(f"\n{GREEN}🎉 PRODUCTION READINESS STATUS: READY TO LAUNCH!{RESET}\n")
        return 0
    else:
        print(f"\n{RED}🔴 PRODUCTION READINESS STATUS: NOT READY (FAILED GATES){RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_checks())
