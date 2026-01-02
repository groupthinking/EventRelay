
import sys
import os
import asyncio
import logging

# Add src to path
sys.path.append(os.path.abspath("src"))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verification")

async def verify():
    logger.info("Verifying Hybrid AI Setup...")
    
    try:
        logger.info("1. Importing EnhancedVideoExtractor...")
        from youtube_extension.processors.enhanced_extractor import EnhancedVideoExtractor
        logger.info("✅ EnhancedVideoExtractor imported successfully")
        
        logger.info("2. Importing GeminiService...")
        from youtube_extension.services.ai.gemini_service import GeminiService
        logger.info("✅ GeminiService imported successfully")
        
        logger.info("3. Initializing Extractor...")
        extractor = EnhancedVideoExtractor()
        
        # Check if Gemini service was initialized (requires env var, but class structure should exist)
        if hasattr(extractor, 'gemini_service'):
             logger.info(f"✅ Extractor has 'gemini_service' attribute (Value: {extractor.gemini_service})")
        else:
             logger.error("❌ Extractor missing 'gemini_service' attribute")
             
        # Check if construct_prompt method exists
        if hasattr(extractor, '_construct_gemini_prompt'):
            logger.info("✅ _construct_gemini_prompt method exists")
        else:
            logger.error("❌ _construct_gemini_prompt method missing")
            
    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        sys.exit(1)

    logger.info("🎉 Hybrid AI Verification Complete!")

if __name__ == "__main__":
    asyncio.run(verify())
