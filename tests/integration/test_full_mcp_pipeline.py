#!/usr/bin/env python3
"""
Full MCP Pipeline Test - Complete video-to-software automation
Tests: video-ingest → architect → code-gen with real MCP video
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents import get_agent_network, get_emitter

async def test_full_mcp_pipeline():
    """Test complete pipeline with MCP Toolkit video"""
    print("=" * 70)
    print("FULL PIPELINE TEST: Video → Architecture → Code → Build → Deploy")
    print("=" * 70)
    print()

    # MCP Toolkit video (relevant to our work)
    test_video = "https://youtu.be/ButAp5rF69E"
    print(f"Video: NEW MCP Toolkit (8m 53s)")
    print(f"URL: {test_video}")
    print()

    # Get network and emitter
    network = get_agent_network()
    emitter = get_emitter()

    # Track results
    results = {}

    try:
        # STAGE 1: Video Ingest
        print("[1/5] VIDEO INGEST")
        print("-" * 70)

        await emitter.emit("pipeline.event", {
            "event": "stage.started",
            "stage": "video-ingest"
        })

        result_1 = await network.route_to_agent(
            "video-ingest",
            "process_video_markdown",
            {
                "video_url": test_video,
                "extract_transcript": True,
                "analyze_content": True
            }
        )

        results['video-ingest'] = result_1
        success_1 = result_1.get('status') == 'success'

        if success_1:
            print(f"✅ Status: SUCCESS")
            print(f"   Video ID: {result_1.get('video_id')}")
            print(f"   Title: {result_1.get('metadata', {}).get('title', 'N/A')[:60]}...")
            print(f"   Transcript: {len(result_1.get('transcript', []))} segments")
            print()
        else:
            print(f"✗ Status: FAILED - {result_1.get('error')}")
            return

        # STAGE 2: Architecture Determination (Tri-Model Consensus)
        print("[2/5] ARCHITECTURE DETERMINATION")
        print("-" * 70)
        print("   Using Tri-Model Consensus: Grok 4.1 + Claude Opus 4.5 + Gemini 3 Pro...")
        print()

        await emitter.emit("pipeline.event", {
            "event": "stage.started",
            "stage": "architect"
        })

        # Get tri-model consensus for architecture decision
        from agents.mcp_tools import get_tri_model_consensus_tool
        consensus_tool = get_tri_model_consensus_tool()

        # Build architecture prompt from video data
        video_title = result_1.get('metadata', {}).get('title', 'Unknown Video')
        video_duration = result_1.get('metadata', {}).get('duration', 'Unknown')

        architecture_prompt = f"""You are an expert software architect. Analyze this video concept and recommend the best technology stack for a web application.

VIDEO CONCEPT: "{video_title}"
DURATION: {video_duration}
TOPICS: MCP servers, Docker, TypeScript, AI integration, server deployment

Recommend the optimal architecture in JSON format:
{{
    "app_type": "type of application to build (be specific)",
    "framework": "primary framework (e.g., Next.js 14, NestJS, Express)",
    "tech_stack": ["list", "of", "key", "technologies"],
    "features": ["core", "features", "to", "implement"],
    "deployment": "deployment platform (vercel, railway, aws, etc.)",
    "confidence": 0.0-1.0
}}

Return ONLY the JSON, no additional text."""

        consensus_result = await consensus_tool.get_consensus(
            prompt=architecture_prompt,
            task_type="architecture",
            require_all=False  # Don't fail if a model is unavailable
        )

        if consensus_result.get("status") == "success":
            # Parse consensus response (extract JSON from markdown if needed)
            import json
            consensus_response = consensus_result.get("consensus_response", "{}")

            # Extract JSON from markdown fences if present
            if "```json" in consensus_response:
                consensus_response = consensus_response.split("```json")[1].split("```")[0]
            elif "```" in consensus_response:
                consensus_response = consensus_response.split("```")[1].split("```")[0]

            try:
                architecture = json.loads(consensus_response.strip())
            except json.JSONDecodeError:
                # Fallback to default if parsing fails
                architecture = {
                    "app_type": "mcp_toolkit_demo",
                    "framework": "Next.js 14",
                    "tech_stack": ["TypeScript", "Tailwind CSS", "Docker", "MCP"],
                    "features": ["mcp_server_catalog", "one_click_install", "containerization"],
                    "deployment": "vercel",
                    "confidence": 0.9
                }

            print(f"✅ Status: CONSENSUS ACHIEVED")
            print(f"   Models: {consensus_result.get('models_queried')}/3")
            print(f"   Agreement: {consensus_result.get('agreement_score', 0):.2f}")
            print(f"   Consensus Confidence: {consensus_result.get('consensus_confidence', 0):.2f}")
            print(f"   App Type: {architecture.get('app_type', 'Unknown')}")
            print(f"   Framework: {architecture.get('framework', 'Unknown')}")
            print(f"   Tech Stack: {', '.join(architecture.get('tech_stack', [])[:4])}")
            print(f"   Features: {', '.join(architecture.get('features', [])[:3])}")
            print()

            results['architect'] = {
                "status": "success",
                "architecture": architecture,
                "consensus": consensus_result
            }
        else:
            # Fallback if consensus fails
            print(f"⚠️  Consensus failed: {consensus_result.get('error')}")
            architecture = {
                "app_type": "mcp_toolkit_demo",
                "framework": "Next.js 14",
                "tech_stack": ["TypeScript", "Tailwind CSS", "Docker", "MCP"],
                "features": ["mcp_server_catalog", "one_click_install", "containerization"],
                "deployment": "vercel",
                "confidence": 0.9
            }
            results['architect'] = {
                "status": "fallback",
                "architecture": architecture
            }
            print()

        # STAGE 3: Code Generation
        print("[3/5] CODE GENERATION")
        print("-" * 70)
        print("   Generating full-stack application with Gemini 3...")
        print()

        await emitter.emit("pipeline.event", {
            "event": "stage.started",
            "stage": "code-gen"
        })

        # Import and use existing AI code generator
        from youtube_extension.backend.ai_code_generator import AICodeGenerator

        generator = AICodeGenerator()

        # Prepare video analysis for code generator
        video_analysis = {
            "video_data": {
                "video_id": result_1.get('video_id'),
                "video_url": test_video
            },
            "extracted_info": {
                "title": result_1.get('metadata', {}).get('title', 'MCP Toolkit Demo'),
                "technologies": ["Docker", "MCP", "Claude", "TypeScript"],
                "features": ["mcp_catalog", "containerization", "ai_integration"]
            },
            "ai_analysis": result_1.get('analysis', {}),
            "metadata": result_1.get('metadata', {})
        }

        project_config = {
            "type": architecture['app_type'],
            "features": architecture['features'],
            "title": result_1.get('metadata', {}).get('title', 'MCP Toolkit Demo')
        }

        # Generate full-stack project
        code_result = await generator.generate_fullstack_project(
            video_analysis,
            project_config
        )

        results['code-gen'] = {
            "status": "success",
            **code_result
        }

        print(f"✅ Status: SUCCESS")
        print(f"   Project Path: {code_result.get('project_path')}")
        print(f"   Framework: {code_result.get('framework')}")
        print(f"   Files Created: {len(code_result.get('files_created', []))}")
        print(f"   Entry Point: {code_result.get('entry_point')}")
        print()

        # List generated files
        files = code_result.get('files_created', [])
        if files:
            print("   Generated Files:")
            for file_path in files[:10]:
                print(f"     - {file_path}")
            if len(files) > 10:
                print(f"     ... and {len(files) - 10} more")
        print()

        # STAGE 4: Build Validation
        print("[4/5] BUILD VALIDATION")
        print("-" * 70)
        print("   Running npm install && npm run build...")
        print()

        await emitter.emit("pipeline.event", {
            "event": "stage.started",
            "stage": "build-validator"
        })

        result_4 = await network.route_to_agent(
            "build-validator",
            "validate_build",
            {
                "project_path": code_result.get('project_path'),
                "max_fix_attempts": 3
            }
        )

        results['build-validator'] = result_4
        success_4 = result_4.get('status') == 'success'

        if success_4:
            print(f"✅ Status: BUILD SUCCESS")
            print(f"   Attempts: {result_4.get('attempts', 1)}")
            print(f"   Build Time: {result_4.get('build_time', 'N/A')}")
            if result_4.get('fixes_applied'):
                print(f"   Fixes Applied: {len(result_4['fixes_applied'])}")
                for fix in result_4['fixes_applied']:
                    print(f"     - {fix.get('diagnosis', 'Auto-fix')}")
        else:
            print(f"⚠️  Status: BUILD FAILED")
            print(f"   Attempts: {result_4.get('attempts', 0)}")
            errors = result_4.get('errors', [])
            print(f"   Errors: {len(errors)}")
            if errors:
                for i, error in enumerate(errors[:3], 1):
                    print(f"     {i}. [{error.get('stage')}] {error.get('message', '')[:100]}...")
        print()

        # STAGE 5: Deployment
        print("[5/5] DEPLOYMENT")
        print("-" * 70)
        print("   Deploying to GitHub + Vercel...")
        print()

        await emitter.emit("pipeline.event", {
            "event": "stage.started",
            "stage": "deployer"
        })

        # Only deploy if build succeeded
        if success_4:
            result_5 = await network.route_to_agent(
                "deployer",
                "deploy_to_github_and_vercel",
                {
                    "project_path": code_result.get('project_path'),
                    "project_name": None  # Auto-detect from directory name
                }
            )

            results['deployer'] = result_5
            success_5 = result_5.get('status') == 'success'

            if success_5:
                print(f"✅ Status: DEPLOYMENT SUCCESS")
                if result_5.get('github_deployed'):
                    print(f"   GitHub: {result_5.get('github_url')}")
                if result_5.get('vercel_deployed'):
                    print(f"   Vercel: {result_5.get('vercel_url')}")
            else:
                print(f"⚠️  Status: DEPLOYMENT FAILED")
                errors = result_5.get('errors', [])
                if errors:
                    for error in errors:
                        print(f"   [{error.get('stage')}] {error.get('message', '')[:100]}...")
        else:
            print(f"⏭️  Skipped (build failed)")
            results['deployer'] = {
                "status": "skipped",
                "reason": "Build validation failed"
            }
        print()

        await emitter.emit("pipeline.event", {
            "event": "pipeline.completed",
            "success": True,
            "stages": 5
        })

    except Exception as e:
        print(f"\n✗ Pipeline Error: {e}")
        import traceback
        traceback.print_exc()

        await emitter.emit("pipeline.event", {
            "event": "pipeline.failed",
            "error": str(e)
        })

    finally:
        # Clean up all resources
        await emitter.close()

        # Close video processor if it was used
        try:
            from agents.mcp_tools import get_youtube_tool
            youtube_tool = get_youtube_tool()
            await youtube_tool.close()
        except Exception as e:
            logger.debug(f"Error closing YouTube tool: {e}")

        # Close build validator if it was used
        try:
            from agents.mcp_tools import get_build_validator_tool
            build_validator = get_build_validator_tool()
            await build_validator.close()
        except Exception as e:
            logger.debug(f"Error closing Build Validator tool: {e}")

        # Close deployment tool if it was used
        try:
            from agents.mcp_tools import get_deployment_tool
            deployment_tool = get_deployment_tool()
            await deployment_tool.close()
        except Exception as e:
            logger.debug(f"Error closing Deployment tool: {e}")

        # Close consensus tool if it was used
        try:
            from agents.mcp_tools import get_tri_model_consensus_tool
            consensus_tool = get_tri_model_consensus_tool()
            await consensus_tool.close()
        except Exception as e:
            logger.debug(f"Error closing Consensus tool: {e}")

    # Summary
    print()
    print("=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print()
    print("Results:")
    print(f"  [1] Video Ingest:     {'✅ SUCCESS' if results.get('video-ingest', {}).get('status') == 'success' else '✗ FAILED'}")
    print(f"  [2] Architecture:     {'✅ SUCCESS' if results.get('architect', {}).get('status') == 'success' else '✗ FAILED'}")
    print(f"  [3] Code Generation:  {'✅ SUCCESS' if results.get('code-gen', {}).get('status') == 'success' else '✗ FAILED'}")
    print(f"  [4] Build Validation: {'✅ SUCCESS' if results.get('build-validator', {}).get('status') == 'success' else '⚠️  FAILED'}")

    deployer_status = results.get('deployer', {}).get('status')
    if deployer_status == 'success':
        status_text = '✅ SUCCESS'
    elif deployer_status == 'skipped':
        status_text = '⏭️  SKIPPED'
    else:
        status_text = '⚠️  FAILED'
    print(f"  [5] Deployment:       {status_text}")
    print()

    if results.get('code-gen', {}).get('status') == 'success':
        print("✨ Full-stack application generated successfully!")
        print(f"📁 Location: {results['code-gen'].get('project_path')}")
        print()

        # Show deployment URLs if deployed
        deployer_result = results.get('deployer', {})
        if deployer_result.get('status') == 'success':
            print("🚀 Deployment Complete:")
            if deployer_result.get('github_url'):
                print(f"   GitHub:  {deployer_result['github_url']}")
            if deployer_result.get('vercel_url'):
                print(f"   Live App: {deployer_result['vercel_url']}")
            print()
        else:
            print("Next Steps:")
            print("  1. Review generated code")
            if results.get('build-validator', {}).get('status') != 'success':
                print("  2. Fix build errors")
                print("  3. Deploy to GitHub + Vercel")
            else:
                print("  2. Deploy manually: gh repo create && vercel deploy")

if __name__ == "__main__":
    asyncio.run(test_full_mcp_pipeline())
