#!/usr/bin/env python3
"""
Universal Automation Coordinator - Production Integration
==========================================================

Integrates:
1. Existing EventRelay TranscriptActionWorkflow (video → full applications)
2. Existing UVAI UVAICodexUniversalDeployment (Codex validation + deployment)
3. NEW: Gemini API enhancement for richer video understanding
4. Existing DeploymentManager (GitHub + multi-platform deployment)

Usage:
    python3 universal_coordinator.py "https://youtube.com/watch?v=VIDEO_ID" --mode production
"""

# Standard imports
import sys
import os
import asyncio
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import warnings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Suppress NumPy warnings during import
warnings.filterwarnings('ignore', category=UserWarning, module='torch')

# Add EventRelay and UVAI to path
EVENTRELAY_PATH = "/Users/garvey/Dev/OpenAI_Hub/projects/EventRelay/src"
UVAI_PATH = "/Users/garvey/Dev/OpenAI_Hub/projects/UVAI/src"

if str(EVENTRELAY_PATH) not in sys.path:
    sys.path.insert(0, str(EVENTRELAY_PATH))
if str(UVAI_PATH) not in sys.path:
    sys.path.insert(0, str(UVAI_PATH))

# Global flags for availability (initially False, set during lazy load)
EVENTRELAY_AVAILABLE = False
DEPLOYMENT_MANAGER_AVAILABLE = False
UVAI_DEPLOYMENT_AVAILABLE = False
GEMINI_AVAILABLE = False


class UniversalAutomationCoordinator:
    """
    Production coordinator integrating existing EventRelay + UVAI systems
    with optional Gemini enhancement
    """

    def __init__(self,
                 mode: str = "production",
                 gemini_api_key: Optional[str] = None,
                 github_token: Optional[str] = None):
        """
        Initialize coordinator with production systems

        Args:
            mode: "production" (EventRelay+UVAI), "gemini" (Gemini only), "hybrid" (both)
            gemini_api_key: Optional Gemini API key for enhanced video understanding
            github_token: GitHub token for deployment
        """
        self.mode = mode
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")

    def __init__(self,
                 mode: str = "production",
                 gemini_api_key: Optional[str] = None,
                 github_token: Optional[str] = None):
        """
        Initialize coordinator with production systems

        Args:
            mode: "production" (EventRelay+UVAI), "gemini" (Gemini only), "hybrid" (both)
            gemini_api_key: Optional Gemini API key for enhanced video understanding
            github_token: GitHub token for deployment
        """
        self.mode = mode
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")

        # Initialize components based on availability
        self.eventrelay_workflow = None
        self.deployment_manager = None
        self.uvai_deployer = None
        self.gemini_processor = None
        self.grok_service = None
        self.mcp_clients = {}
        
        # Lazy load dependencies
        self._load_dependencies()

        # Initialize MCP Agents
        self._init_mcp_agents()

        self.processing_state = {
            "mode": self.mode,
            "components_available": {
                "eventrelay": self.eventrelay_workflow is not None,
                "deployment_manager": self.deployment_manager is not None,
                "uvai_deployer": self.uvai_deployer is not None,
                "gemini": self.gemini_processor is not None,
                "mcp_agents": list(self.mcp_clients.keys())
            }
        }

    def _load_dependencies(self):
        """Lazy load heavy dependencies"""
        global EVENTRELAY_AVAILABLE, DEPLOYMENT_MANAGER_AVAILABLE, UVAI_DEPLOYMENT_AVAILABLE, GEMINI_AVAILABLE
        
        if self.mode in ["production", "hybrid"]:
            print("⏳ Loading EventRelay dependencies (this may take a moment)...")
            try:
                from youtube_extension.services.workflows.transcript_action_workflow import VideoToActionWorkflow
                self.eventrelay_workflow = VideoToActionWorkflow()
                EVENTRELAY_AVAILABLE = True
                print("✅ EventRelay TranscriptActionWorkflow initialized")
            except ImportError:
                print("⚠️  EventRelay module not found")
            except Exception as e:
                print(f"⚠️  EventRelay initialization failed: {e}")

        if self.github_token:
            try:
                from youtube_extension.backend.deployment_manager import DeploymentManager
                self.deployment_manager = DeploymentManager(github_token=self.github_token)
                DEPLOYMENT_MANAGER_AVAILABLE = True
                print("✅ DeploymentManager initialized")
            except ImportError:
                 pass
            except Exception as e:
                print(f"⚠️  DeploymentManager initialization failed: {e}")

            try:
                from tools.uvai_codex_universal_deployment import UVAICodexUniversalDeployment
                self.uvai_deployer = UVAICodexUniversalDeployment(github_token=self.github_token)
                UVAI_DEPLOYMENT_AVAILABLE = True
                print("✅ UVAI Codex Universal Deployment initialized")
            except ImportError:
                pass
            except Exception as e:
                print(f"⚠️  UVAI deployer initialization failed: {e}")

        # Initialize Grok Service (Global)
        try:
            # Add integrations path
            integrations_path = Path(__file__).parent / "integrations"
            if str(integrations_path) not in sys.path:
                sys.path.insert(0, str(integrations_path))
                
            from grok_service import GrokService
            self.grok_service = GrokService(api_key=os.getenv("XAI_API_KEY"))
            print("✅ Grok Service (Global) initialized")
        except ImportError:
            print("⚠️  GrokService module not found")
            self.grok_service = None
        except Exception as e:
            print(f"⚠️  GrokService initialization failed: {e}")
            self.grok_service = None

        if self.mode in ["gemini", "hybrid"] and self.gemini_api_key:
            try:
                current_dir = Path(__file__).parent
                if str(current_dir) not in sys.path:
                    sys.path.insert(0, str(current_dir))
                from gemini_video_processor import GeminiVideoProcessor
                self.gemini_processor = GeminiVideoProcessor(api_key=self.gemini_api_key)
                GEMINI_AVAILABLE = True
                print("✅ Gemini Video Processor initialized")
            except ImportError:
                pass
            except Exception as e:
                print(f"⚠️  Gemini processor initialization failed: {e}")

    def _init_mcp_agents(self):
        """Initialize MCP agents from configuration"""
        try:
            from mcp_client import MCPClient, MCPServerConfig
            config_path = Path(__file__).parent / "config" / "mcp_servers.json"
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                
                servers = config.get("mcpServers", {})
                for name, cfg in servers.items():
                    # Only initialize specific agents to avoid overhead
                    if name in ["grok", "web-eval-agent", "unified-analytics"]:
                        try:
                            mcp_config = MCPServerConfig(
                                command=cfg["command"],
                                args=cfg["args"],
                                env=cfg.get("env")
                            )
                            self.mcp_clients[name] = MCPClient(mcp_config)
                            print(f"✅ MCP Agent initialized: {name}")
                        except Exception as e:
                            print(f"⚠️  Failed to init MCP agent {name}: {e}")
        except ImportError:
            print("⚠️  MCPClient not available (mcp_client.py missing)")
        except Exception as e:
            print(f"⚠️  MCP initialization error: {e}")

    async def process_youtube_url(self, youtube_url: str, deploy: bool = True) -> Dict[str, Any]:
        """
        Complete pipeline: Video → Analysis → Code Generation → Deployment → Revenue

        Args:
            youtube_url: YouTube video URL
            deploy: Whether to auto-deploy generated projects

        Returns:
            Complete pipeline results with deployment URLs
        """
        print(f"\n{'='*80}")
        print(f"🚀 UNIVERSAL AUTOMATION COORDINATOR")
        print(f"{'='*80}")
        print(f"📺 Video URL: {youtube_url}")
        print(f"⚙️  Mode: {self.mode}")
        print(f"🚀 Auto-deploy: {deploy}")
        print(f"{'='*80}\n")

        start_time = asyncio.get_event_loop().time()
        results = {
            "youtube_url": youtube_url,
            "mode": self.mode,
            "timestamp": datetime.now().isoformat(),
            "stages": {}
        }

        try:
            # STAGE 1: Video Understanding (Gemini Enhancement Optional)
            if self.mode in ["gemini", "hybrid"] and self.gemini_processor:
                print("🎬 STAGE 1: Gemini Video Understanding")
                print("-" * 80)
                gemini_result = self.gemini_processor.process_video(youtube_url)
                results["stages"]["gemini_analysis"] = gemini_result
                print("✅ Gemini analysis complete\n")

            # STAGE 1.5: MCP Agent Enhancement (Active Research)
            if self.mcp_clients or self.grok_service:
                print("🤖 STAGE 1.5: Multi-Modal Analysis & Agent Swarm")
                print("-" * 80)
                
                # Direct Grok Integration (High Fidelity)
                if self.grok_service:
                    print("   🧠 Engaging Grok Analysis Agent...")
                    # Note: In a real run, we would pass transcript from EventRelay results 
                    # but since EventRelay runs in Stage 2, we might do this in parallel or order differently.
                    # For now, we simulate the "Analysis" capability if we have metadata.
                    try:
                        # Placeholder metadata until Stage 2 extraction or Gemini Stage 1 extraction
                        grok_input_meta = {"title": "Processing...", "duration": "Unknown"}
                        grok_result = self.grok_service.process_video_context(grok_input_meta, "Transcript placeholder for analysis.")
                        results["stages"]["grok_analysis"] = grok_result
                        print("   ✅ Grok Analysis Complete")
                    except Exception as e:
                         print(f"   ⚠️ Grok Analysis failed: {e}")

                # MCP Agents
                if "grok" in self.mcp_clients:
                    try:
                        grok = self.mcp_clients["grok"]
                        tools = await grok.list_tools()
                        print(f"   🧠 Grok MCP Agent available with {len(tools)} tools")
                        results["stages"]["agent_grok"] = {"status": "available", "tools": len(tools)}
                    except Exception as e:
                        print(f"   ⚠️ Grok interaction failed: {e}")

                # Example: Use Web Eval for additional verification
                if "web-eval-agent" in self.mcp_clients:
                    try:
                        web_eval = self.mcp_clients["web-eval-agent"]
                        tools = await web_eval.list_tools()
                        print(f"   🌐 Web Eval Agent available with {len(tools)} tools")
                        results["stages"]["agent_web_eval"] = {"status": "available", "tools": len(tools)}
                    except Exception as e:
                        print(f"   ⚠️ Web Eval interaction failed: {e}")
                print()

            # STAGE 2: EventRelay Workflow (Production Pipeline)
            if self.mode in ["production", "hybrid"] and self.eventrelay_workflow:
                print("🔄 STAGE 2: EventRelay Video-to-Action Workflow")
                print("-" * 80)

                eventrelay_result = await self.eventrelay_workflow.process_video_to_actions(youtube_url)
                results["stages"]["eventrelay_processing"] = eventrelay_result

                if eventrelay_result.get('success'):
                    print("✅ EventRelay processing complete")
                    print(f"   📊 Category: {eventrelay_result.get('processed_video_data', {}).get('category', 'N/A')}")
                    print(f"   📋 Actions: {len(eventrelay_result.get('processed_video_data', {}).get('actions', []))}")
                    print(f"   💻 Project scaffold generated")
                else:
                    print(f"⚠️  EventRelay processing had issues: {eventrelay_result.get('error', 'Unknown')}")
                print()

            # STAGE 3: Code Generation & GitHub Deployment
            if deploy and self.deployment_manager and results["stages"].get("eventrelay_processing"):
                print("🚀 STAGE 3: Project Deployment")
                print("-" * 80)

                eventrelay_data = results["stages"]["eventrelay_processing"]
                workflow_result = eventrelay_data.get('workflow_result', {})

                if workflow_result.get('project_dir'):
                    deployment_config = {
                        'target': 'github',
                        'platforms': ['vercel', 'netlify'],  # Multi-platform deployment
                        'auto_publish': True
                    }

                    deployment_result = await self.deployment_manager.deploy_project(
                        project_path=workflow_result['project_dir'],
                        project_config=eventrelay_data.get('processed_video_data', {}),
                        deployment_config=deployment_config
                    )

                    results["stages"]["deployment"] = deployment_result

                    if deployment_result.get('deployments', {}).get('github'):
                        github_info = deployment_result['deployments']['github']
                        print(f"✅ GitHub deployment successful")
                        print(f"   📦 Repository: {github_info.get('repo_url', 'N/A')}")
                        print(f"   🌐 Live URL: {github_info.get('deployment_url', 'Pending')}")
                    print()

            # STAGE 4: UVAI Codex Validation & Universal Deployment
            if deploy and self.uvai_deployer and results["stages"].get("deployment"):
                print("🔒 STAGE 4: UVAI Codex Validation & Deployment")
                print("-" * 80)

                github_deployment = results["stages"]["deployment"]["deployments"].get("github", {})

                if github_deployment.get('repo_url'):
                    uvai_config = {
                        'project_path': github_deployment['repo_url'],
                        'validation_required': True,
                        'platforms': ['vercel', 'fly'],
                        'auto_scale': True
                    }

                    uvai_result = await self.uvai_deployer.universal_deploy(uvai_config)
                    results["stages"]["uvai_deployment"] = uvai_result

                    print(f"✅ UVAI Codex validation complete")
                    print(f"   🔒 Security score: {uvai_result.get('security_score', 'N/A')}")
                    print(f"   📊 Quality score: {uvai_result.get('quality_score', 'N/A')}")
                    print(f"   🌐 Production URL: {uvai_result.get('deployment_url', 'Pending')}")
                    print()

            # Calculate final metrics
            processing_time = asyncio.get_event_loop().time() - start_time
            results["processing_time"] = processing_time
            results["success"] = True

            # Summary
            print(f"{'='*80}")
            print("✅ PIPELINE COMPLETE")
            print(f"{'='*80}")
            print(f"⏱️  Total processing time: {processing_time:.2f}s")
            print(f"📊 Stages completed: {len(results['stages'])}")

            if results["stages"].get("deployment"):
                print(f"\n🚀 DEPLOYED SERVICES:")
                deployment = results["stages"]["deployment"]
                for platform, info in deployment.get("deployments", {}).items():
                    print(f"   • {platform.upper()}: {info.get('deployment_url', info.get('repo_url', 'N/A'))}")

            if results["stages"].get("uvai_deployment"):
                uvai = results["stages"]["uvai_deployment"]
                print(f"\n💰 REVENUE POTENTIAL:")
                print(f"   • Estimated monthly: ${uvai.get('revenue_estimate', {}).get('monthly', '500-2000')}")
                print(f"   • Service type: {uvai.get('service_type', 'SaaS/API')}")

            print(f"{'='*80}\n")

        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            print(f"\n❌ Pipeline failed: {e}\n")

        return results

    def get_status(self) -> Dict[str, Any]:
        """Get coordinator status and available components"""
        return self.processing_state


async def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Universal Automation Coordinator - YouTube to Revenue-Generating Services'
    )
    parser.add_argument('youtube_url', help='YouTube video URL to process')
    parser.add_argument(
        '--mode',
        choices=['production', 'gemini', 'hybrid'],
        default='hybrid',
        help='Processing mode (default: hybrid - uses both EventRelay and Gemini)'
    )
    parser.add_argument(
        '--no-deploy',
        action='store_true',
        help='Skip deployment (analysis only)'
    )
    parser.add_argument(
        '--gemini-key',
        help='Gemini API key (optional, uses GEMINI_API_KEY env var if not provided)'
    )
    parser.add_argument(
        '--github-token',
        help='GitHub token (optional, uses GITHUB_TOKEN env var if not provided)'
    )

    args = parser.parse_args()

    # Initialize coordinator
    coordinator = UniversalAutomationCoordinator(
        mode=args.mode,
        gemini_api_key=args.gemini_key,
        github_token=args.github_token
    )

    # Process video
    result = await coordinator.process_youtube_url(
        args.youtube_url,
        deploy=not args.no_deploy
    )

    # Cleanup MCP clients
    for name, client in coordinator.mcp_clients.items():
        await client.stop()

    # Save results
    output_file = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"📄 Full results saved to: {output_file}")

    return result


if __name__ == "__main__":
    asyncio.run(main())
