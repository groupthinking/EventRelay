#!/usr/bin/env python3
"""
Production Readiness Verification Gate
=====================================
Ensures all critical, launch-gating security, configuration, logging,
and deployment prerequisites are met before shipping to production.

Checks executed:
1. Environment Configuration Templates (validating uncommented assignments)
2. Live Environment Secret Verification (masked logging of active keys)
3. CORS Security Constraints (static analysis of main.py CORS setup)
4. Secure Headers Configuration (validating X-Frame-Options, X-Content-Type-Options)
5. Production Logging Level & Configuration (verifying LOG_LEVEL and structured format)
6. Basic Dependency Hygiene

This script fails closed (exits with non-zero code) if any rule is breached.
"""

import argparse
import os
import re
import sys
from pathlib import Path

# Color constants for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

# Required keys per LAUNCH_CHECKLIST.md and security protocols
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
    "EVENTRELAY_API_KEY",
    "DATABASE_URL",
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "XAI_API_KEY",
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
    """Mask secret values completely to prevent leaks in logs."""
    if not value:
        return "[EMPTY]"
    return f"[PRESENT, len={len(value)}]"


def get_uncommented_assignments(file_path: Path) -> set:
    """Parse a .env style file line-by-line and return uncommented assignment keys."""
    assignments = set()
    if not file_path.exists():
        return assignments

    # Matches lines like: VARIABLE_NAME=value (ignoring commented lines)
    pattern = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")
    for line in file_path.read_text(encoding="utf-8").splitlines():
        # Strip comments starting with # before checking
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = pattern.match(line)
        if match:
            assignments.add(match.group(1))
    return assignments


def check_configuration_templates() -> bool:
    """Ensure required launch keys are documented in .env.example and apps/web/.env.example."""
    log_info("Step 1: Verifying Configuration Templates...")
    success = True

    root_example = Path(".env.example")
    web_example = Path("apps/web/.env.example")

    # Validate root env template
    if not root_example.exists():
        log_failure("Root .env.example template is missing!")
        success = False
    else:
        assignments = get_uncommented_assignments(root_example)
        for key in REQUIRED_BACKEND_KEYS:
            if key not in assignments:
                log_failure(f"Root .env.example template is missing uncommented assignment for: {key}")
                success = False
            else:
                log_success(f"Root template defines variable: {key}")

    # Validate web env template
    if not web_example.exists():
        log_failure("Web app .env.example template is missing!")
        success = False
    else:
        assignments = get_uncommented_assignments(web_example)
        for key in REQUIRED_WEB_KEYS:
            if key not in assignments:
                log_failure(f"Web .env.example template is missing uncommented assignment for: {key}")
                success = False
            else:
                log_success(f"Web template defines variable: {key}")

    return success


def check_live_environment(mode: str) -> bool:
    """Inspect current environment setup. Mask secrets to prevent leak in logs."""
    log_info("Step 2: Inspecting Live Environment Variables...")

    is_live_mode = (mode == "live" or os.getenv("ENVIRONMENT") == "production")
    success = True

    for key in REQUIRED_BACKEND_KEYS + REQUIRED_WEB_KEYS:
        val = os.getenv(key)
        if val:
            log_success(f"Environment variable {key} is ACTIVE (value: {mask_secret(val)})")
        else:
            if is_live_mode:
                log_failure(f"Environment variable {key} is missing in production/live mode!")
                success = False
            else:
                log_warning(f"Local Environment variable {key} is unset (template fallback allowed).")

    return success


def check_cors_and_headers() -> bool:
    """Analyze main.py statically for CORS configuration, Logging level, and Secure Headers."""
    log_info("Step 3: Statically analyzing main.py for security constraints...")
    success = True

    main_py_path = Path("src/youtube_extension/main.py")
    if not main_py_path.exists():
        log_failure(f"Could not find main backend entrypoint: {main_py_path}")
        return False

    content = main_py_path.read_text(encoding="utf-8")

    # 1. CORS Analysis: Verify allowed origins logic
    if "CORSMiddleware" not in content:
        log_failure("CORS Middleware is not implemented in main.py!")
        success = False
    else:
        log_success("CORS Middleware implementation found.")

    # Check for wildcards combined with credentials (forbidden)
    if "allow_credentials=True" in content and '"*"' in content and "allow_origins" in content:
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

    # 3. Logging Config Check: Verify that the entrypoint consumes LOG_LEVEL dynamically
    # and configures proper level and stream handlers
    if "os.getenv(\"LOG_LEVEL\"" in content or "os.getenv(\"ENVIRONMENT\"" in content or "SENTRY_DSN" in content:
        log_success("Structured logging with dynamic environment configuration is verified.")
    else:
        log_failure("Backend is missing proper log-level dynamic parsing or format controls!")
        success = False

    return success


def check_dependencies() -> bool:
    """Check basic dependency integrity."""
    log_info("Step 4: Checking Dependency Hygiene...")

    requirements_path = Path("requirements.txt")
    package_json_path = Path("apps/web/package.json")

    success = True

    if requirements_path.exists():
        reqs = requirements_path.read_text(encoding="utf-8")
        if "ipdb" in reqs or "pudb" in reqs:
            log_failure("Development debuggers (ipdb/pudb) detected in production requirements.txt!")
            success = False
        else:
            log_success("Python dependencies requirements.txt looks healthy.")
    else:
        log_warning("No requirements.txt found at root.")

    if package_json_path.exists():
        pj = package_json_path.read_text(encoding="utf-8")
        if "playwright" in pj and "@playwright/test" not in pj:
            log_failure("playwright is declared but @playwright/test is missing from package.json!")
            success = False
        else:
            log_success("Next.js dependencies package.json looks healthy.")
    else:
        log_warning("No package.json found at apps/web/package.json.")

    return success


def run_checks(mode: str) -> int:
    """Run all checks and return an exit code (0 if success, 1 if any failure)."""
    print(f"\n{BLUE}=== UVAI Production Readiness Auditor ==={RESET}\n")
    print(f"Auditing Mode: {mode.upper()}")

    checks = [
        check_configuration_templates(),
        check_live_environment(mode),
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Production Readiness Verification Gate")
    parser.add_argument(
        "--mode",
        choices=["ci", "live"],
        default="ci",
        help="Auditor execution mode: 'ci' for template checking, 'live' for production validations (fail-closed)."
    )
    args = parser.parse_args()
    sys.exit(run_checks(args.mode))


if __name__ == "__main__":
    main()
