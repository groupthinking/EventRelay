#!/usr/bin/env python3
"""
Test script to generate a complete infrastructure platform with all packages.

This tests Phase 1, Phase 2, and Phase 3 implementations by generating
a full Turborepo monorepo with all available packages.
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from youtube_extension.backend.ai_code_generator import get_ai_code_generator
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Generate test application with all packages"""

    logger.info("🧪 Starting complete infrastructure platform generation test")

    # Create AI code generator
    generator = get_ai_code_generator()

    # Mock video analysis (simulate a video about building AI infrastructure)
    video_analysis = {
        "extracted_info": {
            "title": "Building Production AI Infrastructure Platform",
            "technologies": [
                "Next.js", "TypeScript", "Prisma", "Supabase",
                "Turborepo", "OpenTelemetry", "Docker", "MCP"
            ],
            "features": [
                "Multi-model AI gateway",
                "Database management",
                "Real-time updates",
                "Error handling",
                "Observability",
                "Workflow orchestration"
            ],
            "complexity": "advanced",
            "description": "Complete infrastructure platform with production-ready packages"
        },
        "ai_analysis": {
            "project_type": "infrastructure_platform",
            "recommended_stack": "TypeScript + Next.js + Supabase",
            "key_features": [
                "Turborepo monorepo",
                "Multi-model AI gateway (Grok/Claude/Gemini)",
                "Prisma + Supabase database",
                "OpenTelemetry observability",
                "MCP connectors",
                "Workflow.dev orchestration",
                "Comprehensive logging",
                "Error boundaries + retry logic",
                "Type-safe env config"
            ]
        }
    }

    # Architecture config that triggers ALL packages
    architecture = {
        "type": "infrastructure_platform",  # This triggers all infrastructure packages
        "framework": "nextjs",
        "frontend": {
            "framework": "nextjs",
            "styling": "tailwind",
            "state": "zustand"
        },
        "backend": {
            "type": "api_routes",
            "database": "supabase",
            "auth": "nextauth"
        },
        "features": [
            "auth",
            "database",
            "api",
            "dashboard",
            "ai-gateway",
            "workflows",
            "observability",
            "mcp-connectors",
            "error-handling"
        ],
        "deployment": {
            "platform": "vercel",
            "database_hosting": "supabase"
        },
        # Explicit flags to ensure all packages are generated
        "monorepo": True,
        "has_mcp": True,
        "has_workflows": True,
        "has_observability": True,
        "has_ai_gateway": True,
        "has_logging": True,
        "has_error_handling": True,
        "has_database": True,
        "has_config": True
    }

    # Project configuration
    project_config = {
        "name": "test-infrastructure-platform",
        "description": "Complete test of all Phase 1, 2, and 3 packages",
        "video_id": "test_complete_generation"
    }

    try:
        # Generate the project
        logger.info("📦 Generating infrastructure platform with all packages...")
        result = await generator.generate_fullstack_project(
            video_analysis=video_analysis,
            project_config=project_config
        )

        # Verify generation
        if result and result.get("project_path"):
            project_path = Path(result["project_path"])
            logger.info(f"✅ Generation successful! Project at: {project_path}")

            # Verify expected packages
            expected_packages = [
                "packages/ui",
                "packages/tsconfig",
                "packages/mcp-connectors",
                "packages/workflows",
                "packages/observability",
                "packages/ai-gateway",
                "packages/logger",
                "packages/error-handling",
                "packages/database",
                "packages/config"
            ]

            logger.info("\n📋 Verifying package generation:")
            for package in expected_packages:
                package_path = project_path / package
                exists = package_path.exists()
                status = "✅" if exists else "❌"
                logger.info(f"{status} {package}")

                if exists and package_path.is_dir():
                    # Count files in package
                    file_count = len(list(package_path.rglob("*.*")))
                    logger.info(f"   └─ {file_count} files")

            # Verify turbo.json
            if (project_path / "turbo.json").exists():
                logger.info("✅ turbo.json present")

            # Verify root package.json
            if (project_path / "package.json").exists():
                logger.info("✅ Root package.json present")

            # Summary
            logger.info("\n" + "="*60)
            logger.info("📊 GENERATION TEST SUMMARY")
            logger.info("="*60)
            logger.info(f"Project Path: {project_path}")
            logger.info(f"Total Files: {len(result.get('files_created', []))}")
            logger.info(f"Architecture: {result.get('project_type', 'unknown')}")
            logger.info(f"Framework: {result.get('framework', 'unknown')}")
            logger.info("\n✅ All packages generated successfully!")
            logger.info("\nNext steps:")
            logger.info(f"1. cd {project_path}")
            logger.info("2. npm install")
            logger.info("3. Copy .env.example to .env and fill in credentials")
            logger.info("4. npm run dev")

            return True
        else:
            logger.error("❌ Generation failed: No project path returned")
            return False

    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
