import os
import sys
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    skill_name = "analytics-dashboard"
    logger.info(f"Skill {skill_name} invoked")
    context = os.getenv("SKILL_CONTEXT", "{}")
    logger.info(f"Context: {context}")
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        logger.info("GEMINI_API_KEY is present")
    else:
        logger.warning("GEMINI_API_KEY is missing")
    print(json.dumps({"status": "success", "skill": skill_name}))

if __name__ == "__main__":
    main()
