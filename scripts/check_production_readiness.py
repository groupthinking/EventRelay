import os
import sys
import logging
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("production-readiness")

def check_env_vars():
    logger.info("Checking environment variables...")
    critical_vars = [
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "NEXTAUTH_SECRET",
        "UPSTASH_REDIS_REST_URL"
    ]
    missing = [v for v in critical_vars if not os.getenv(v)]
    if missing:
        logger.warning(f"Missing critical environment variables: {missing}")
    else:
        logger.info("✅ All critical environment variables are set.")

def check_cors_config():
    logger.info("Checking CORS configuration...")
    main_path = Path("src/youtube_extension/main.py")
    if main_path.exists():
        content = main_path.read_text()
        # Verify that allowed origins are restricted and loopbacks are rejected in production
        if "_IS_PRODUCTION = _ENVIRONMENT == \"production\"" in content and "if _IS_PRODUCTION and _is_loopback_origin(_origin):" in content:
            logger.info("✅ CORS production safety checks found in main.py.")
        else:
            logger.error("❌ CORS production safety checks (loopback rejection) NOT found in main.py.")
    else:
        logger.error("❌ src/youtube_extension/main.py not found.")

def check_log_levels():
    logger.info("Checking log configuration...")
    log_config_path = Path("src/youtube_extension/backend/config/logging_config.py")
    if log_config_path.exists():
        content = log_config_path.read_text()
        if "level=logging.INFO" in content or "level=os.getenv" in content:
            logger.info("✅ Logging level configuration looks appropriate for production.")
        else:
            logger.warning("⚠️ Logging level might be too verbose (DEBUG).")
    else:
        # Fallback to main.py check
        main_path = Path("src/youtube_extension/main.py")
        if main_path.exists():
            content = main_path.read_text()
            if "logging.basicConfig(level=logging.INFO)" in content:
                logger.info("✅ Default logging level set to INFO in main.py.")

def check_security_middleware():
    logger.info("Checking security middleware...")
    main_path = Path("src/youtube_extension/main.py")
    if main_path.exists():
        content = main_path.read_text()
        required_headers = ["X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection"]
        found = [h for h in required_headers if h in content]
        if len(found) == len(required_headers):
            logger.info(f"✅ Security headers middleware found: {found}")
        else:
            logger.error(f"❌ Missing security headers: {set(required_headers) - set(found)}")

        if "APIKeyAuthMiddleware" in content or "api_key_auth" in content:
            logger.info("✅ API Key authentication middleware found.")
        else:
            logger.warning("⚠️ API Key authentication middleware not found in main.py.")

def check_dependencies():
    logger.info("Checking production dependencies...")
    req_path = Path("requirements.txt")
    if req_path.exists():
        content = req_path.read_text()
        prod_deps = ["fastapi", "uvicorn", "pydantic", "sqlalchemy"]
        missing = [d for d in prod_deps if d not in content.lower()]
        if not missing:
            logger.info("✅ Core production dependencies found in requirements.txt.")
        else:
            logger.error(f"❌ Missing core dependencies in requirements.txt: {missing}")

def main():
    logger.info("--- EventRelay Production Readiness Audit ---")
    check_env_vars()
    check_cors_config()
    check_log_levels()
    check_security_middleware()
    check_dependencies()
    logger.info("Audit complete.")

if __name__ == "__main__":
    main()
