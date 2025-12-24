#!/usr/bin/env python3
"""
MULTI-LLM VIDEO PROCESSOR
A robust video processor that can switch between multiple LLM providers:
- OpenAI (ChatGPT)
- Anthropic (Claude)
- GROK4 (xAI)
- Google AI (Gemini)

Provides fallback mechanisms and performance benchmarking
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import aiohttp
import requests
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass
from enum import Enum

# Google AI imports
import google.generativeai as genai

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logging.warning("python-dotenv not available")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [MULTI_LLM] %(message)s',
    handlers=[
        logging.FileHandler('multi_llm_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("multi_llm_processor")

class LLMProvider(Enum):
    """Available LLM providers"""
    OPENAI_GPT4O = "gpt-4o"
    OPENAI_GPT4O_MINI = "gpt-4o-mini"
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"
    GROK_4 = "grok-4-0709"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_1_5_PRO = "gemini-1.5-pro"

@dataclass
class LLMResult:
    """Result from LLM call"""
    provider: LLMProvider
    content: str
    processing_time: float
    success: bool
    error_message: Optional[str] = None
    tokens_used: Optional[int] = None

class MultiLLMVideoProcessor:
    """Multi-LLM video processor with fallback mechanisms"""
    
    def __init__(self):
        # Load API keys from environment variables
        self.openai_api_key = os.getenv('OPENAI_API_KEY') or os.getenv('REACT_APP_OPENAI_API_KEY')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.grok_api_key = (
            os.getenv('XAI_GROK4_API') or 
            os.getenv('XAI_GROK4_OR_3_API') or 
            os.getenv('XAI_GROK_3_OR_2_ONLY_API')
        )
        self.gemini_api_key = (
            os.getenv('GEMINI_API_KEY') or 
            os.getenv('GOOGLE_API_KEY')
        )
        
        self.output_dir = Path('multi_llm_results')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Google AI if available
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_client = genai.GenerativeModel('gemini-2.5-flash')
            logger.info("✅ Google AI (Gemini) initialized")
        
        # Provider priority order (most reliable first)
        self.provider_priority = [
            LLMProvider.OPENAI_GPT4O,
            LLMProvider.CLAUDE_3_5_SONNET,
            LLMProvider.GEMINI_2_5_FLASH,
            LLMProvider.OPENAI_GPT4O_MINI,
            LLMProvider.CLAUDE_3_HAIKU,
            LLMProvider.GROK_4,
            LLMProvider.GEMINI_1_5_PRO
        ]
        
        logger.info("🎯 MULTI-LLM VIDEO PROCESSOR INITIALIZED")
        logger.info(f"✅ OpenAI API Key: {'✅ Found' if self.openai_api_key else '❌ Missing'}")
        logger.info(f"✅ Claude API Key: {'✅ Found' if self.anthropic_api_key else '❌ Missing'}")
        logger.info(f"✅ GROK4 API Key: {'✅ Found' if self.grok_api_key else '❌ Missing'}")
        logger.info(f"✅ Gemini API Key: {'✅ Found' if self.gemini_api_key else '❌ Missing'}")
    
    def extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        parsed = urlparse(url)
        if parsed.hostname in ['youtube.com', 'www.youtube.com', 'youtu.be']:
            if parsed.path == '/watch':
                return parse_qs(parsed.query)['v'][0]
            elif parsed.hostname == 'youtu.be':
                return parsed.path[1:]
        return url
    
    async def process_video_with_multi_llm(self, video_url: str) -> Dict[str, Any]:
        """Process video using multiple LLM providers with fallback"""
        
        start_time = time.time()
        video_id = self.extract_video_id(video_url)
        
        logger.info(f"🚀 MULTI-LLM PROCESSING: {video_id}")
        
        # Create analysis tasks
        tasks = [
            ("transcription", "Transcribe the audio content from this video with timestamps"),
            ("summarization", "Provide a comprehensive summary of this video's content"),
            ("key_insights", "Extract the most important insights and takeaways from this video"),
            ("action_generation", "Generate specific, actionable steps based on this video's content"),
            ("implementation_plan", "Create a detailed implementation plan for applying the video's concepts")
        ]
        
        results = {}
        successful_providers = set()
        
        for task_name, prompt in tasks:
            logger.info(f"🤖 Executing {task_name} with multi-LLM fallback")
            
            # Try each provider in priority order
            for provider in self.provider_priority:
                try:
                    result = await self._execute_with_provider(provider, prompt, video_url)
                    if result.success:
                        results[task_name] = result
                        successful_providers.add(provider)
                        logger.info(f"✅ {task_name} completed with {provider.value}")
                        break
                    else:
                        logger.warning(f"⚠️ {provider.value} failed for {task_name}: {result.error_message}")
                except Exception as e:
                    logger.error(f"❌ {provider.value} error for {task_name}: {e}")
                    continue
        
        # Generate comprehensive report
        processing_time = time.time() - start_time
        comprehensive_result = await self._generate_comprehensive_report(
            video_id, video_url, results, successful_providers, processing_time
        )
        
        # Save results
        save_result = await self._save_multi_llm_results(video_id, comprehensive_result)
        
        return {
            'success': True,
            'video_id': video_id,
            'video_url': video_url,
            'comprehensive_result': comprehensive_result,
            'save_result': save_result,
            'processing_time': processing_time,
            'successful_providers': list(successful_providers),
            'timestamp': datetime.now().isoformat()
        }
    
    async def _execute_with_provider(self, provider: LLMProvider, prompt: str, video_url: str) -> LLMResult:
        """Execute task with specific LLM provider"""
        
        start_time = time.time()
        
        try:
            if provider in [LLMProvider.OPENAI_GPT4O, LLMProvider.OPENAI_GPT4O_MINI]:
                content = await self._execute_with_openai(provider, prompt, video_url)
            elif provider in [LLMProvider.CLAUDE_3_5_SONNET, LLMProvider.CLAUDE_3_HAIKU]:
                content = await self._execute_with_claude(provider, prompt, video_url)
            elif provider == LLMProvider.GROK_4:
                content = await self._execute_with_grok4(prompt, video_url)
            elif provider in [LLMProvider.GEMINI_2_5_FLASH, LLMProvider.GEMINI_1_5_PRO]:
                content = await self._execute_with_gemini(provider, prompt, video_url)
            else:
                raise Exception(f"Unknown provider: {provider}")
            
            processing_time = time.time() - start_time
            
            return LLMResult(
                provider=provider,
                content=content,
                processing_time=processing_time,
                success=True
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return LLMResult(
                provider=provider,
                content="",
                processing_time=processing_time,
                success=False,
                error_message=str(e)
            )
    
    async def _execute_with_openai(self, provider: LLMProvider, prompt: str, video_url: str) -> str:
        """Execute with OpenAI API"""
        
        if not self.openai_api_key:
            raise Exception("OpenAI API key not available")
        
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": provider.value,
            "messages": [
                {"role": "system", "content": "You are an expert video content analyzer."},
                {"role": "user", "content": f"Analyze this YouTube video: {video_url}\n\n{prompt}"}
            ],
            "max_tokens": 2000,
            "temperature": 0.3
        }
        
        # Create SSL context to handle certificate issues
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
                else:
                    raise Exception(f"OpenAI API error: {response.status}")
    
    async def _execute_with_claude(self, provider: LLMProvider, prompt: str, video_url: str) -> str:
        """Execute with Claude API"""
        
        if not self.anthropic_api_key:
            raise Exception("Claude API key not available")
        
        headers = {
            "x-api-key": self.anthropic_api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": provider.value,
            "max_tokens": 2000,
            "messages": [
                {"role": "user", "content": f"Analyze this YouTube video: {video_url}\n\n{prompt}"}
            ]
        }
        
        # Create SSL context to handle certificate issues
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=30
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return result['content'][0]['text']
                else:
                    raise Exception(f"Claude API error: {response.status}")
    
    async def _execute_with_grok4(self, prompt: str, video_url: str) -> str:
        """Execute with GROK4 API"""
        
        if not self.grok_api_key:
            raise Exception("GROK4 API key not available")
        
        headers = {
            "Authorization": f"Bearer {self.grok_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "grok-4-0709",
            "messages": [
                {"role": "system", "content": "You are an expert video content analyzer."},
                {"role": "user", "content": f"Analyze this YouTube video: {video_url}\n\n{prompt}"}
            ],
            "max_tokens": 2000,
            "temperature": 0.3
        }
        
        # Create SSL context to handle certificate issues
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
                else:
                    raise Exception(f"GROK4 API error: {response.status}")
    
    async def _execute_with_gemini(self, provider: LLMProvider, prompt: str, video_url: str) -> str:
        """Execute with Google AI (Gemini)"""
        
        if not self.gemini_api_key:
            raise Exception("Gemini API key not available")
        
        try:
            full_prompt = f"Analyze this YouTube video: {video_url}\n\n{prompt}"
            response = self.gemini_client.generate_content(full_prompt)
            return response.text
        except Exception as e:
            raise Exception(f"Gemini execution failed: {e}")
    
    async def _generate_comprehensive_report(self, video_id: str, video_url: str, 
                                          results: Dict[str, LLMResult], 
                                          successful_providers: set,
                                          processing_time: float) -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        
        # Organize results by task
        task_results = {}
        for task_name, result in results.items():
            task_results[task_name] = {
                'provider': result.provider.value,
                'content': result.content,
                'processing_time': result.processing_time,
                'success': result.success
            }
        
        # Generate recommendations
        recommendations = []
        if len(successful_providers) >= 3:
            recommendations.append("Multiple LLM providers working well - system is robust")
        elif len(successful_providers) == 0:
            recommendations.append("No LLM providers working - check API keys and connectivity")
        else:
            recommendations.append(f"Limited LLM availability - only {len(successful_providers)} providers working")
        
        # Provider-specific recommendations
        if LLMProvider.OPENAI_GPT4O in successful_providers:
            recommendations.append("OpenAI GPT-4o performing well - good for complex analysis")
        if LLMProvider.CLAUDE_3_5_SONNET in successful_providers:
            recommendations.append("Claude 3.5 Sonnet performing well - good for detailed insights")
        if LLMProvider.GEMINI_2_5_FLASH in successful_providers:
            recommendations.append("Gemini 2.5 Flash performing well - good for fast processing")
        
        return {
            'video_id': video_id,
            'video_url': video_url,
            'task_results': task_results,
            'successful_providers': [p.value for p in successful_providers],
            'total_tasks': len(results),
            'successful_tasks': len([r for r in results.values() if r.success]),
            'processing_time': processing_time,
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _save_multi_llm_results(self, video_id: str, comprehensive_result: Dict[str, Any]) -> Dict[str, Any]:
        """Save multi-LLM results"""
        
        logger.info(f"💾 Saving multi-LLM results for {video_id}")
        
        result_file = self.output_dir / f"{video_id}_multi_llm_results.json"
        
        result_data = {
            'video_id': video_id,
            'processing_timestamp': datetime.now().isoformat(),
            'comprehensive_result': comprehensive_result,
            'file_path': str(result_file),
            'processing_method': 'multi_llm_processor'
        }
        
        with open(result_file, 'w') as f:
            json.dump(result_data, f, indent=2, default=str)
        
        logger.info(f"✅ Multi-LLM results saved to: {result_file}")
        
        return {
            'success': True,
            'file_path': str(result_file),
            'total_tasks': comprehensive_result['total_tasks'],
            'successful_tasks': comprehensive_result['successful_tasks']
        }

async def main():
    """Main execution function"""
    
    if len(sys.argv) < 2:
        print("Usage: python multi_llm_video_processor.py <video_url>")
        print("Example: python multi_llm_video_processor.py https://www.youtube.com/watch?v=aircAruvnKk")
        sys.exit(1)
    
    video_url = sys.argv[1]
    processor = MultiLLMVideoProcessor()
    
    try:
        result = await processor.process_video_with_multi_llm(video_url)
        
        if result['success']:
            print(f"\n🎯 MULTI-LLM PROCESSOR SUCCESS:")
            print(f"   Video ID: {result['video_id']}")
            print(f"   Total Tasks: {result['comprehensive_result']['total_tasks']}")
            print(f"   Successful Tasks: {result['comprehensive_result']['successful_tasks']}")
            print(f"   Processing Time: {result['processing_time']:.3f}s")
            print(f"   Results File: {result['save_result']['file_path']}")
            
            print(f"\n🤖 SUCCESSFUL PROVIDERS:")
            for provider in result['successful_providers']:
                print(f"   ✅ {provider}")
            
            print(f"\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(result['comprehensive_result']['recommendations'], 1):
                print(f"   {i}. {rec}")
            
            print(f"\n📋 TASK RESULTS:")
            for task_name, task_data in result['comprehensive_result']['task_results'].items():
                status = "✅" if task_data['success'] else "❌"
                print(f"   {status} {task_name}: {task_data['provider']} ({task_data['processing_time']:.2f}s)")
        else:
            print(f"❌ PROCESSING FAILED: {result.get('error', 'Unknown error')}")
            sys.exit(1)
        
        return result
        
    except Exception as e:
        print(f"❌ PROCESSING FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
