import logging
import os
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("production-readiness")


def check_env_vars():
    logger.info("Checking environment variables...")
    critical_vars = ["GEMINI_API_KEY", "OPENAI_API_KEY", "STRIPE_SECRET_KEY"]
    missing = [v for v in critical_vars if not os.getenv(v)]
    if missing:
        is_production = (
            os.getenv("APP_ENV") == "production"
            or os.getenv("ENVIRONMENT") == "production"
        )
        if is_production:
            logger.error(f"❌ Missing critical env vars in production: {missing}")
            return True
        else:
            logger.warning(f"Missing critical env vars (non-fatal warning): {missing}")
    return False


def check_cors():
    main_path = Path("src/youtube_extension/main.py")
    if not main_path.exists():
        return True
    content = main_path.read_text()
    if "_IS_PRODUCTION = _ENVIRONMENT == \"production\"" in content:
        logger.info("✅ CORS safety checks found.")
        return False
    logger.error("❌ CORS safety checks missing.")
    return True


def check_headers():
    main_path = Path("src/youtube_extension/main.py")
    if not main_path.exists():
        return True
    content = main_path.read_text()
    if "X-Frame-Options" in content and "X-Content-Type-Options" in content:
        logger.info("✅ Security headers found.")
        return False
    logger.error("❌ Security headers missing.")
    return True


def check_logging():
    logger.info("Checking production logging configurations...")
    main_path = Path("src/youtube_extension/main.py")
    if not main_path.exists():
        logger.error("❌ main.py not found.")
        return True

    content = main_path.read_text()

    # 1. Check if we configure logging at DEBUG level by default
    if "level=logging.DEBUG" in content or "level=logging.root.setLevel(logging.DEBUG)" in content:
        logger.error("❌ Production logging cannot default to DEBUG level (leaks sensitive info).")
        return True

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
                logger.error("❌ Sentry send_default_pii must not be hardcoded to True.")
                return True

    if has_pii_check:
        logger.info("✅ Sentry PII safety check configured.")
    else:
        logger.warning("Sentry PII safety check not found (ensure PII is not sent to Sentry).")

    logger.info("✅ Production logging configuration checks passed.")
    return False


def check_dependencies():
    logger.info("Checking dependency safety...")
    has_error = False

    # 1. Static file check for wildcards / unsafe patterns
    req_path = Path("requirements.txt")
    if req_path.exists():
        reqs = req_path.read_text()
        for line in reqs.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "==" in line:
                parts = line.split("==")
                if len(parts) > 1 and parts[1].strip() == "*":
                    logger.error(f"❌ Unsafe wildcard version found in requirements.txt: {line}")
                    has_error = True
    else:
        logger.warning("requirements.txt not found.")

    pkg_path = Path("package.json")
    if pkg_path.exists():
        pkg = pkg_path.read_text()
        if '"*"' in pkg or "'*'" in pkg:
            logger.error("❌ Unsafe wildcard version '*' found in package.json.")
            has_error = True
    else:
        logger.warning("package.json not found.")

    # 2. Dynamic check via safety/npm-audit if available
    try:
        # Check safety (Python)
        if subprocess.run(["which", "safety"], capture_output=True).returncode == 0:
            logger.info("Running dynamic dependency safety scan (safety check)...")
            res = subprocess.run(["safety", "check", "-r", "requirements.txt"], capture_output=True, text=True)
            if res.returncode != 0:
                logger.warning(f"Safety check found potential issues:\n{res.stdout or res.stderr}")
        else:
            logger.info("safety is not installed; skipping dynamic Python dependency scan.")
    except Exception as e:
        logger.warning(f"Failed to run safety check: {e}")

    try:
        # Check npm audit (Node)
        if subprocess.run(["which", "npm"], capture_output=True).returncode == 0 and pkg_path.exists():
            logger.info("Running dynamic dependency security scan (npm audit)...")
            res = subprocess.run(["npm", "audit"], capture_output=True, text=True)
            if "high" in res.stdout.lower() or "critical" in res.stdout.lower():
                logger.warning("npm audit flagged potential high/critical vulnerabilities.")
        else:
            logger.info("npm is not available or package.json missing; skipping dynamic Node dependency scan.")
    except Exception as e:
        logger.warning(f"Failed to run npm audit: {e}")

    if has_error:
        logger.error("❌ Dependency safety check failed.")
        return True

    logger.info("✅ Dependency safety checks passed.")
    return False


def main():
    errors = [check_cors(), check_headers(), check_logging(), check_dependencies(), check_env_vars()]
    if any(errors):
        logger.error("❌ Audit FAILED.")
        sys.exit(1)
    logger.info("✅ Audit PASSED.")


if __name__ == "__main__":
    main()
