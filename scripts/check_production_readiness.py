import os
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("production-readiness")

def check_env_vars():
    logger.info("Checking environment variables...")
    critical_vars = ["GEMINI_API_KEY", "OPENAI_API_KEY", "STRIPE_SECRET_KEY"]
    missing = [v for v in critical_vars if not os.getenv(v)]
    if missing:
        logger.warning(f"Missing critical env vars (non-fatal warning): {missing}")
    return False

def check_cors():
    main_path = Path("src/youtube_extension/main.py")
    if not main_path.exists(): return True
    content = main_path.read_text()
    if "_IS_PRODUCTION = _ENVIRONMENT == \"production\"" in content:
        logger.info("✅ CORS safety checks found.")
        return False
    logger.error("❌ CORS safety checks missing.")
    return True

def check_headers():
    main_path = Path("src/youtube_extension/main.py")
    if not main_path.exists(): return True
    content = main_path.read_text()
    if "X-Frame-Options" in content and "X-Content-Type-Options" in content:
        logger.info("✅ Security headers found.")
        return False
    logger.error("❌ Security headers missing.")
    return True

def main():
    errors = [check_cors(), check_headers(), check_env_vars()]
    if any(errors):
        logger.error("❌ Audit FAILED.")
        sys.exit(1)
    logger.info("✅ Audit PASSED.")

if __name__ == "__main__":
    main()
