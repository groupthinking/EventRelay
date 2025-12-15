#!/usr/bin/env python3
"""
Revenue Pipeline: YouTube URL → Live Deployed Application
==========================================================

End-to-end pipeline that connects:
1. YouTube video processing (enhanced_video_processor.py)
2. AI code generation (ai_code_generator.py)
3. Automated deployment (Vercel CLI)

This is the monetizable product flow.
"""

import asyncio
import logging
import os
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# Import our components
from .enhanced_video_processor import EnhancedVideoProcessor
from .ai_code_generator import get_ai_code_generator

logger = logging.getLogger(__name__)


class RevenuePipeline:
    """
    End-to-end pipeline from YouTube video to deployed application
    """

    def __init__(self, auto_deploy: bool = True):
        """
        Initialize revenue pipeline

        Args:
            auto_deploy: Whether to automatically deploy to Vercel after generation
        """
        self.video_processor = EnhancedVideoProcessor()
        self.code_generator = get_ai_code_generator()
        self.auto_deploy = auto_deploy

        # Verify Vercel CLI is available
        self.vercel_available = self._check_vercel_cli()
        if self.auto_deploy and not self.vercel_available:
            logger.warning("⚠️ Vercel CLI not found - automatic deployment disabled")
            self.auto_deploy = False

        logger.info("✅ Revenue Pipeline initialized")

    def _check_vercel_cli(self) -> bool:
        """Check if Vercel CLI is installed"""
        try:
            result = subprocess.run(
                ['vercel', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"✅ Vercel CLI found: {result.stdout.strip()}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return False

    async def process_video_to_deployment(
        self,
        youtube_url: str,
        project_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete pipeline: YouTube URL → Live Deployment

        Args:
            youtube_url: YouTube video URL to process
            project_config: Optional project configuration overrides

        Returns:
            Pipeline result with deployment URL
        """
        logger.info(f"🚀 Starting revenue pipeline for: {youtube_url}")
        pipeline_start = datetime.now()

        try:
            # Step 1: Process video
            logger.info("📹 Step 1/4: Processing video...")
            video_result = await self.video_processor.process_video(youtube_url)

            if not video_result.get('success'):
                raise RuntimeError("Video processing failed")

            logger.info(f"✅ Video processed: {video_result['metadata']['title']}")

            # Step 2: Transform to code generator format
            logger.info("🔄 Step 2/4: Transforming data for code generation...")
            video_analysis = self._transform_to_generator_format(video_result)

            # Step 3: Generate code
            logger.info("🤖 Step 3/4: Generating application code...")
            if project_config is None:
                project_config = self._create_project_config(video_result)

            generation_result = await self.code_generator.generate_fullstack_project(
                video_analysis=video_analysis,
                project_config=project_config
            )

            project_path = generation_result['project_path']
            logger.info(f"✅ Code generated at: {project_path}")

            # Step 4: Deploy (if enabled)
            deployment_url = None
            if self.auto_deploy:
                logger.info("🚀 Step 4/4: Deploying to Vercel...")
                deployment_url = await self._deploy_to_vercel(project_path)
                logger.info(f"✅ Deployed to: {deployment_url}")
            else:
                logger.info("⏭️  Step 4/4: Auto-deploy disabled, skipping deployment")

            # Calculate metrics
            pipeline_duration = (datetime.now() - pipeline_start).total_seconds()

            return {
                'success': True,
                'video_url': youtube_url,
                'video_title': video_result['metadata']['title'],
                'project_path': project_path,
                'deployment_url': deployment_url,
                'pipeline_duration_seconds': pipeline_duration,
                'steps_completed': {
                    'video_processing': True,
                    'code_generation': True,
                    'deployment': deployment_url is not None
                },
                'metadata': {
                    'video_id': video_result['video_id'],
                    'channel': video_result['metadata'].get('channel'),
                    'files_generated': len(generation_result.get('files_created', [])),
                    'architecture': generation_result.get('project_type'),
                    'framework': generation_result.get('framework')
                },
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Revenue pipeline failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'video_url': youtube_url,
                'timestamp': datetime.now().isoformat()
            }

    def _transform_to_generator_format(self, video_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform video processor output to AI code generator input format
        """
        metadata = video_result.get('metadata', {})
        transcript = video_result.get('transcript', {})
        ai_analysis = video_result.get('ai_analysis', {})

        # Extract technologies from analysis
        technologies = []
        if isinstance(ai_analysis.get('Key Concepts'), list):
            technologies.extend(ai_analysis['Key Concepts'][:5])
        elif isinstance(ai_analysis.get('Key Concepts'), str):
            technologies = [ai_analysis['Key Concepts']]

        # Extract features from analysis
        features = []
        if isinstance(ai_analysis.get('Related Topics'), list):
            features.extend(ai_analysis['Related Topics'][:5])
        elif isinstance(ai_analysis.get('Related Topics'), str):
            features = [ai_analysis['Related Topics']]

        # Map difficulty to complexity
        difficulty = ai_analysis.get('Difficulty Level', 'Intermediate')
        complexity_map = {
            'Beginner': 'simple',
            'Intermediate': 'moderate',
            'Advanced': 'advanced'
        }
        complexity = complexity_map.get(difficulty, 'moderate')

        return {
            'extracted_info': {
                'title': metadata.get('title', 'Generated Application'),
                'description': metadata.get('description', ''),
                'technologies': technologies,
                'features': features,
                'complexity': complexity,
                'duration': metadata.get('duration', 'Unknown'),
                'channel': metadata.get('channel', 'Unknown')
            },
            'ai_analysis': {
                'project_type': self._infer_project_type(ai_analysis),
                'recommended_stack': self._infer_stack(ai_analysis, technologies),
                'key_features': self._extract_key_features(ai_analysis),
                'content_summary': ai_analysis.get('Content Summary', ''),
                'technical_details': ai_analysis.get('Technical Details', ''),
                'code_generation_potential': ai_analysis.get('Code Generation Potential', '')
            },
            'video_data': {
                'video_id': video_result.get('video_id'),
                'video_url': video_result.get('video_url'),
                'transcript': transcript.get('text', ''),
                'transcript_confidence': transcript.get('confidence', 0.0)
            }
        }

    def _infer_project_type(self, ai_analysis: Dict[str, Any]) -> str:
        """Infer project type from AI analysis"""
        content = str(ai_analysis).lower()

        if any(keyword in content for keyword in ['agent', 'autonomous', 'mcp', 'tool']):
            return 'agent'
        elif any(keyword in content for keyword in ['infrastructure', 'platform', 'monorepo']):
            return 'infrastructure_platform'
        elif any(keyword in content for keyword in ['saas', 'subscription', 'dashboard']):
            return 'saas'
        elif any(keyword in content for keyword in ['game', 'interactive', 'canvas']):
            return 'game'
        else:
            return 'fullstack_app'

    def _infer_stack(self, ai_analysis: Dict[str, Any], technologies: list) -> str:
        """Infer technology stack from analysis"""
        tech_str = ' '.join(str(t).lower() for t in technologies)
        content = str(ai_analysis).lower()
        combined = f"{tech_str} {content}"

        if 'typescript' in combined or 'next' in combined:
            return 'TypeScript + Next.js + Supabase'
        elif 'react' in combined:
            return 'React + Node.js + PostgreSQL'
        elif 'python' in combined:
            return 'Python + FastAPI + PostgreSQL'
        else:
            return 'TypeScript + Next.js + Supabase'  # Default

    def _extract_key_features(self, ai_analysis: Dict[str, Any]) -> list:
        """Extract key features for implementation"""
        features = []

        # Extract from Technical Details
        tech_details = ai_analysis.get('Technical Details', '')
        if tech_details:
            features.append(tech_details[:100])

        # Extract from Code Generation Potential
        code_potential = ai_analysis.get('Code Generation Potential', '')
        if code_potential:
            features.append(code_potential[:100])

        # Add learning path as feature
        learning_path = ai_analysis.get('Learning Path', '')
        if learning_path:
            features.append(f"Learning path: {learning_path[:80]}")

        return features[:5] if features else ['Full-stack application']

    def _create_project_config(self, video_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create project configuration from video result"""
        metadata = video_result.get('metadata', {})
        video_id = video_result.get('video_id', 'unknown')

        # Sanitize title for project name
        title = metadata.get('title', 'generated-app')
        project_name = title.lower()
        project_name = ''.join(c if c.isalnum() or c in '-_' else '-' for c in project_name)
        project_name = project_name[:50]  # Limit length

        return {
            'name': project_name,
            'description': metadata.get('description', '')[:200],
            'video_id': video_id,
            'type': 'fullstack_app',
            'monetization': {
                'model': 'freemium',
                'payment_processor': 'stripe'
            }
        }

    async def _deploy_to_vercel(self, project_path: str) -> Optional[str]:
        """
        Deploy project to Vercel and return deployment URL
        """
        try:
            project_dir = Path(project_path)

            if not project_dir.exists():
                raise FileNotFoundError(f"Project path not found: {project_path}")

            # Check for Vercel token
            vercel_token = os.getenv('VERCEL_TOKEN')
            if not vercel_token:
                logger.warning("VERCEL_TOKEN not set - deployment may require browser login")

            # Install dependencies first
            logger.info("📦 Installing dependencies...")
            npm_result = subprocess.run(
                ['npm', 'install'],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes
            )

            if npm_result.returncode != 0:
                logger.error(f"npm install failed: {npm_result.stderr}")
                raise RuntimeError("Dependency installation failed")

            logger.info("✅ Dependencies installed")

            # Deploy to Vercel
            logger.info("🚀 Deploying to Vercel...")
            deploy_cmd = ['vercel', '--prod', '--yes']

            if vercel_token:
                deploy_cmd.extend(['--token', vercel_token])

            deploy_result = subprocess.run(
                deploy_cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes
            )

            if deploy_result.returncode == 0:
                # Extract URL from output
                output = deploy_result.stdout
                # Vercel outputs the URL in the last line typically
                lines = output.strip().split('\n')
                for line in reversed(lines):
                    if 'vercel.app' in line or 'https://' in line:
                        # Extract URL
                        import re
                        url_match = re.search(r'https://[^\s]+', line)
                        if url_match:
                            deployment_url = url_match.group(0)
                            logger.info(f"✅ Deployed successfully: {deployment_url}")
                            return deployment_url

                logger.warning("Deployment succeeded but couldn't parse URL")
                return "https://vercel.app/deployment-successful"
            else:
                logger.error(f"Vercel deployment failed: {deploy_result.stderr}")
                raise RuntimeError("Vercel deployment failed")

        except subprocess.TimeoutExpired:
            logger.error("Deployment timed out")
            return None
        except Exception as e:
            logger.error(f"Deployment error: {e}")
            return None


def get_revenue_pipeline(auto_deploy: bool = True) -> RevenuePipeline:
    """Factory function to get revenue pipeline instance"""
    return RevenuePipeline(auto_deploy=auto_deploy)


# Example usage
async def main():
    """Example usage of revenue pipeline"""
    pipeline = get_revenue_pipeline(auto_deploy=True)

    # Example: Process a YouTube video and deploy
    youtube_url = "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"

    result = await pipeline.process_video_to_deployment(youtube_url)

    if result['success']:
        print(f"✅ SUCCESS!")
        print(f"Video: {result['video_title']}")
        print(f"Project: {result['project_path']}")
        if result['deployment_url']:
            print(f"Live at: {result['deployment_url']}")
        print(f"Duration: {result['pipeline_duration_seconds']:.2f}s")
    else:
        print(f"❌ FAILED: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())
