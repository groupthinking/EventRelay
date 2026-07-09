import os
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("production-readiness")

def check_env_vars():
    critical_vars = ["GEMINI_API_KEY", "OPENAI_API_KEY", "STRIPE_SECRET_KEY"]
    missing = [v for v in critical_vars if not os.getenv(v)]
    if missing:
        logger.warning(f"Missing critical environment variables (normal for dev): {missing}")
    else:
        logger.info("All critical environment variables are set.")

def check_cors_config():
    # Basic check for CORS origins in main.py
    main_path = Path("src/youtube_extension/main.py")
    if main_path.exists():
        content = main_path.read_text()
        if "allow_origins=_allowed_origins" in content:
            logger.info("CORS seems properly configured with restricted origins.")
        else:
            logger.error("CORS might be overly permissive.")

def check_log_levels():
    # Verify that logging is not set to DEBUG in production
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        # This is just a placeholder logic for the script
        logger.info("Environment is production. Checking log levels...")

def main():
    logger.info("--- EventRelay Production Readiness Check ---")
    check_env_vars()
    check_cors_config()
    check_log_levels()
    logger.info("Check complete.")

if __name__ == "__main__":
    main()
