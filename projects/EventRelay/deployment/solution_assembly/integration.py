#!/usr/bin/env python3
"""
Solution Assembly Integration Module
====================================

Integrates the Solution Assembly Engine with the existing YouTube video processing
system in RealLearningAgent.jsx and mcp_server.py.

This module provides:
- MCP tool integration for solution assembly
- React component integration hooks
- WebSocket communication for real-time assembly
- Performance monitoring and caching
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import time

from solution_assembly.engine import SolutionAssemblyEngine, VideoContentAnalyzer, VideoAnalysisResult

logger = logging.getLogger(__name__)


class MCPSolutionAssemblyTool:
    """
    MCP Tool for solution assembly that integrates with the existing mcp_server.py
    """
    
    def __init__(self):
        self.assembly_engine = SolutionAssemblyEngine()
        self.video_analyzer = VideoContentAnalyzer()
        self.cache = {}
        
    async def process_video_and_assemble_solution(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main MCP tool method that processes video and assembles solution
        
        Expected params:
        {
            "video_id": "YouTube video ID",
            "video_metadata": {
                "title": "Video title",
                "description": "Video description"
            },
            "transcript": [{"text": "...", "start": 0, "duration": 5}],
            "assembly_options": {
                "include_tests": true,
                "include_deployment": true,
                "optimization_level": "high"
            }
        }
        """
        try:
            start_time = time.time()
            
            # Extract parameters
            video_id = params.get('video_id', '')
            video_metadata = params.get('video_metadata', {})
            transcript = params.get('transcript', [])
            assembly_options = params.get('assembly_options', {})
            
            # Check cache first
            cache_key = f"{video_id}_{hash(str(assembly_options))}"
            if cache_key in self.cache:
                logger.info(f"Returning cached result for video {video_id}")
                return self.cache[cache_key]
            
            # Step 1: Analyze video content
            video_analysis = self.video_analyzer.analyze_video_content(
                video_id=video_id,
                title=video_metadata.get('title', ''),
                description=video_metadata.get('description', ''),
                transcript=transcript
            )
            
            # Step 2: Assemble solution
            assembly_result = await self.assembly_engine.assemble_solution_from_video(
                video_analysis
            )
            
            # Step 3: Format result for MCP response
            result = {
                'video_analysis': {
                    'video_id': assembly_result.video_analysis.video_id,
                    'title': assembly_result.video_analysis.title,
                    'technical_keywords': assembly_result.video_analysis.technical_keywords,
                    'implementation_requirements': assembly_result.video_analysis.implementation_requirements,
                    'framework_hints': assembly_result.video_analysis.framework_hints,
                    'complexity_score': assembly_result.video_analysis.complexity_score
                },
                'solution': {
                    'main_code': assembly_result.assembled_solution,
                    'test_code': assembly_result.test_code if assembly_options.get('include_tests') else '',
                    'deployment_instructions': assembly_result.deployment_instructions if assembly_options.get('include_deployment') else '',
                    'discovered_sources': len(assembly_result.discovered_code),
                    'source_repositories': [
                        code['repository'] for code in assembly_result.discovered_code 
                        if 'repository' in code
                    ][:5]  # Top 5 sources
                },
                'performance_metrics': assembly_result.performance_metrics,
                'assembly_metadata': {
                    'assembly_timestamp': assembly_result.assembly_timestamp,
                    'processing_time_seconds': time.time() - start_time,
                    'cache_key': cache_key
                }
            }
            
            # Cache result for future use
            self.cache[cache_key] = result
            
            logger.info(f"Solution assembly completed for video {video_id} in {time.time() - start_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Solution assembly failed for video {video_id}: {e}")
            return {
                'error': str(e),
                'video_id': params.get('video_id', ''),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def search_and_discover_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP tool for direct code discovery without video processing
        
        Expected params:
        {
            "search_terms": ["react", "api", "authentication"],
            "language": "javascript",
            "max_results": 10
        }
        """
        try:
            search_terms = params.get('search_terms', [])
            language = params.get('language', 'python')
            max_results = params.get('max_results', 10)
            
            # Use the GitHub connector directly
            github_connector = self.assembly_engine.github_connector
            
            discovered_code = []
            for term in search_terms:
                results = await github_connector.search_repositories({
                    'query': term,
                    'language': language,
                    'sort': 'stars',
                    'order': 'desc',
                    'per_page': max_results // len(search_terms)
                })
                
                if results.get('result', {}).get('items'):
                    for repo in results['result']['items']:
                        discovered_code.append({
                            'repository': f"{repo['owner']['login']}/{repo['name']}",
                            'description': repo.get('description', ''),
                            'stars': repo.get('stargazers_count', 0),
                            'language': repo.get('language', ''),
                            'url': repo.get('html_url', '')
                        })
            
            return {
                'discovered_repositories': discovered_code[:max_results],
                'search_terms': search_terms,
                'total_found': len(discovered_code),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Code discovery failed: {e}")
            return {
                'error': str(e),
                'search_terms': params.get('search_terms', []),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def optimize_existing_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP tool for optimizing existing code using pattern detection
        
        Expected params:
        {
            "code": "# Python code to optimize",
            "optimization_type": "performance|error_handling|structure"
        }
        """
        try:
            code = params.get('code', '')
            optimization_type = params.get('optimization_type', 'performance')
            
            # Use pattern detector and mutator
            pattern_detector = self.assembly_engine.pattern_detector
            mutator = self.assembly_engine.mutator
            
            # Analyze patterns (mock execution data for optimization)
            analysis = await pattern_detector.analyze_execution_patterns()
            
            # Apply optimizations
            optimization_result = await mutator._apply_mutation({
                'protocol': 'user_code',
                'mutation_type': optimization_type,
                'suggested_changes': [
                    'Add error handling',
                    'Improve performance',
                    'Add caching',
                    'Optimize structure'
                ]
            })
            
            return {
                'original_code': code,
                'optimized_code': optimization_result.get('success', False),
                'optimizations_applied': optimization_result.get('changes_applied', []),
                'optimization_type': optimization_type,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Code optimization failed: {e}")
            return {
                'error': str(e),
                'original_code': params.get('code', ''),
                'timestamp': datetime.utcnow().isoformat()
            }


class ReactIntegrationHooks:
    """
    Integration hooks for the React frontend (RealLearningAgent.jsx)
    """
    
    @staticmethod
    def generate_solution_assembly_config():
        """
        Generate configuration for React component integration
        """
        return {
            'mcp_tools': {
                'process_video_and_assemble_solution': {
                    'description': 'Process video and assemble working code solution',
                    'parameters': {
                        'video_id': 'string',
                        'video_metadata': 'object',
                        'transcript': 'array',
                        'assembly_options': 'object'
                    }
                },
                'search_and_discover_code': {
                    'description': 'Search and discover code from multiple sources',
                    'parameters': {
                        'search_terms': 'array',
                        'language': 'string',
                        'max_results': 'number'
                    }
                },
                'optimize_existing_code': {
                    'description': 'Optimize code using pattern detection',
                    'parameters': {
                        'code': 'string',
                        'optimization_type': 'string'
                    }
                }
            },
            'ui_components': {
                'solution_display': {
                    'show_code_tabs': True,
                    'show_deployment_instructions': True,
                    'show_performance_metrics': True,
                    'enable_code_editing': True
                },
                'discovery_interface': {
                    'show_search_suggestions': True,
                    'show_repository_sources': True,
                    'enable_real_time_search': True
                }
            },
            'performance_settings': {
                'enable_caching': True,
                'cache_duration_minutes': 30,
                'enable_background_processing': True,
                'max_concurrent_assemblies': 3
            }
        }
    
    @staticmethod
    def generate_react_component_enhancement():
        """
        Generate React component enhancements for solution assembly
        """
        return '''
// Add to RealLearningAgent.jsx state
const [solutionAssembly, setSolutionAssembly] = useState({
  isAssembling: false,
  assemblyProgress: 0,
  assemblyStep: '',
  result: null,
  error: null
});

// Add to processing function
const processSolutionAssembly = async (videoData, transcript) => {
  setSolutionAssembly(prev => ({ ...prev, isAssembling: true, assemblyProgress: 0 }));
  
  try {
    // Step 1: Video Analysis (20% progress)
    setSolutionAssembly(prev => ({ ...prev, assemblyProgress: 20, assemblyStep: 'Analyzing video content...' }));
    
    // Step 2: Code Discovery (50% progress)
    setSolutionAssembly(prev => ({ ...prev, assemblyProgress: 50, assemblyStep: 'Discovering relevant code...' }));
    
    // Step 3: Solution Assembly (80% progress)
    setSolutionAssembly(prev => ({ ...prev, assemblyProgress: 80, assemblyStep: 'Assembling solution...' }));
    
    // Call MCP tool
    const result = await mcpClient.callTool('process_video_and_assemble_solution', {
      video_id: videoData.video_id,
      video_metadata: {
        title: videoData.title,
        description: videoData.description
      },
      transcript: transcript,
      assembly_options: {
        include_tests: true,
        include_deployment: true,
        optimization_level: 'high'
      }
    });
    
    // Step 4: Complete (100% progress)
    setSolutionAssembly({
      isAssembling: false,
      assemblyProgress: 100,
      assemblyStep: 'Complete',
      result: result,
      error: null
    });
    
  } catch (error) {
    setSolutionAssembly({
      isAssembling: false,
      assemblyProgress: 0,
      assemblyStep: '',
      result: null,
      error: error.message
    });
  }
};

// Add to UI render
{solutionAssembly.result && (
  <div className="solution-assembly-result">
    <h3>🚀 Assembled Solution</h3>
    
    <div className="solution-tabs">
      <button onClick={() => setActiveTab('main')}>Main Code</button>
      <button onClick={() => setActiveTab('tests')}>Tests</button>
      <button onClick={() => setActiveTab('deployment')}>Deployment</button>
      <button onClick={() => setActiveTab('metrics')}>Metrics</button>
    </div>
    
    <div className="solution-content">
      {activeTab === 'main' && (
        <pre><code>{solutionAssembly.result.solution.main_code}</code></pre>
      )}
      {activeTab === 'tests' && (
        <pre><code>{solutionAssembly.result.solution.test_code}</code></pre>
      )}
      {activeTab === 'deployment' && (
        <pre><code>{solutionAssembly.result.solution.deployment_instructions}</code></pre>
      )}
      {activeTab === 'metrics' && (
        <div className="metrics-display">
          <div>Assembly Time: {solutionAssembly.result.performance_metrics.assembly_time_seconds}s</div>
          <div>Quality Score: {solutionAssembly.result.performance_metrics.quality_score}/10</div>
          <div>Source Repositories: {solutionAssembly.result.solution.discovered_sources}</div>
        </div>
      )}
    </div>
    
    <div className="solution-actions">
      <button onClick={() => downloadSolution()}>📥 Download</button>
      <button onClick={() => deploySolution()}>🚀 Deploy</button>
      <button onClick={() => optimizeSolution()}>⚡ Optimize</button>
    </div>
  </div>
)}
        '''


def integrate_with_mcp_server():
    """
    Generate integration code for mcp_server.py
    """
    return '''
# Add to mcp_server.py imports
from solution_assembly.integration import MCPSolutionAssemblyTool

# Add to server initialization
solution_assembly_tool = MCPSolutionAssemblyTool()

# Add to tools list in tools/list handler
solution_assembly_tools = [
    Tool(
        name="process_video_and_assemble_solution",
        description="Process YouTube video and assemble working code solution",
        inputSchema={
            "type": "object",
            "properties": {
                "video_id": {"type": "string"},
                "video_metadata": {"type": "object"},
                "transcript": {"type": "array"},
                "assembly_options": {"type": "object"}
            },
            "required": ["video_id", "transcript"]
        }
    ),
    Tool(
        name="search_and_discover_code",
        description="Search and discover code from multiple sources",
        inputSchema={
            "type": "object",
            "properties": {
                "search_terms": {"type": "array"},
                "language": {"type": "string"},
                "max_results": {"type": "number"}
            },
            "required": ["search_terms"]
        }
    ),
    Tool(
        name="optimize_existing_code",
        description="Optimize code using pattern detection",
        inputSchema={
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "optimization_type": {"type": "string"}
            },
            "required": ["code"]
        }
    )
]

# Add to tools/call handler
elif tool_name == "process_video_and_assemble_solution":
    result = await solution_assembly_tool.process_video_and_assemble_solution(arguments)
elif tool_name == "search_and_discover_code":
    result = await solution_assembly_tool.search_and_discover_code(arguments)
elif tool_name == "optimize_existing_code":
    result = await solution_assembly_tool.optimize_existing_code(arguments)
    '''


# Configuration and settings
SOLUTION_ASSEMBLY_CONFIG = {
    'github': {
        'api_base_url': 'https://api.github.com',
        'search_rate_limit': 30,  # requests per minute
        'file_size_limit': 1048576,  # 1MB
        'max_repositories_per_search': 10
    },
    'assembly': {
        'max_source_files': 20,
        'max_assembly_time_seconds': 300,  # 5 minutes
        'quality_threshold': 6.0,
        'enable_optimization': True
    },
    'caching': {
        'enable_cache': True,
        'cache_ttl_seconds': 1800,  # 30 minutes
        'max_cache_size': 100
    },
    'performance': {
        'max_concurrent_assemblies': 5,
        'enable_background_processing': True,
        'performance_monitoring': True
    }
}


if __name__ == "__main__":
    # Test the integration
    async def test_integration():
        tool = MCPSolutionAssemblyTool()
        
        # Test video processing
        test_params = {
            'video_id': 'test123',
            'video_metadata': {
                'title': 'Building a React API with Node.js',
                'description': 'Learn to create a full-stack application'
            },
            'transcript': [
                {'text': 'Today we will build a React application with a Node.js API', 'start': 0, 'duration': 5},
                {'text': 'We will use Express for the backend and create REST endpoints', 'start': 5, 'duration': 5}
            ],
            'assembly_options': {
                'include_tests': True,
                'include_deployment': True,
                'optimization_level': 'high'
            }
        }
        
        result = await tool.process_video_and_assemble_solution(test_params)
        print(json.dumps(result, indent=2))
    
    # Run test
    asyncio.run(test_integration())