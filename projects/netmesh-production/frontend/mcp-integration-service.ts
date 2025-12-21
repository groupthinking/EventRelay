/**
 * MCP Integration Service
 * Connects React frontend to existing ML/LLM infrastructure
 */

import { io, Socket } from 'socket.io-client';

export interface MCPResponse {
  result?: any;
  error?: { code: number; message: string };
  id?: string;
}

export interface AgentStatus {
  id: string;
  name: string;
  status: 'active' | 'idle' | 'error';
  task: string;
  performance: {
    success_rate: number;
    avg_response_time: number;
    total_requests: number;
  };
}

export interface VideoProcessingResult {
  transcript: Array<{
    timestamp: number;
    text: string;
    confidence: number;
  }>;
  code_segments: Array<{
    timestamp: number;
    code: string;
    language: string;
    explanation: string;
  }>;
  metadata: {
    duration: number;
    skill_category: string;
    difficulty_level: string;
    tools_mentioned: string[];
  };
}

export class MCPIntegrationService {
  private bridgeUrl = 'http://localhost:8004/mcp';
  private orchestratorUrl = 'http://localhost:8001';
  private mcpServerUrl = 'http://localhost:8003'; // Self-correcting executor
  private youtubeServerUrl = 'http://localhost:8005'; // YouTube extension
  private socket: Socket | null = null;

  constructor() {
    this.initializeWebSocket();
  }

  private initializeWebSocket() {
    this.socket = io(this.orchestratorUrl, {
      transports: ['websocket'],
      autoConnect: true
    });

    this.socket.on('connect', () => {
      console.log('Connected to MCP orchestrator');
    });

    this.socket.on('agent_status_update', (data: AgentStatus) => {
      // Emit custom event for React components
      window.dispatchEvent(new CustomEvent('agentStatusUpdate', { detail: data }));
    });

    this.socket.on('video_processing_progress', (data: any) => {
      window.dispatchEvent(new CustomEvent('videoProcessingProgress', { detail: data }));
    });
  }

  // Hybrid Query System (Claude + Grok)
  async hybridQuery(
    query: string, 
    model: 'claude' | 'grok' | 'auto' = 'auto',
    options: {
      use_real_time?: boolean;
      structured_output?: boolean;
      output_schema?: any;
    } = {}
  ): Promise<any> {
    try {
      const response = await fetch(this.bridgeUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          method: 'tools/call',
          params: {
            name: 'hybrid_query',
            arguments: {
              query,
              model,
              ...options
            }
          }
        })
      });

      const result = await response.json();
      if (result.error) {
        throw new Error(result.error.message);
      }

      return result.result;
    } catch (error) {
      console.error('Hybrid query failed:', error);
      throw error;
    }
  }

  // YouTube Video Processing
  async processYouTubeVideo(videoUrl: string): Promise<VideoProcessingResult> {
    const query = `Process YouTube video: ${videoUrl}. Extract transcript with timestamps, identify code segments, and analyze skill content.`;
    
    const result = await this.hybridQuery(query, 'auto', {
      structured_output: true,
      output_schema: {
        type: 'object',
        properties: {
          transcript: { type: 'array' },
          code_segments: { type: 'array' },
          metadata: { type: 'object' }
        }
      }
    });

    return result.result;
  }

  // A2A Agent Coordination
  async getAgentStatuses(): Promise<AgentStatus[]> {
    try {
      const response = await fetch(`${this.orchestratorUrl}/agents/status`);
      return await response.json();
    } catch (error) {
      console.error('Failed to get agent statuses:', error);
      return [];
    }
  }

  async coordinateAgents(task: string, agents: string[]): Promise<any> {
    const query = `Coordinate agents [${agents.join(', ')}] for task: ${task}`;
    return this.hybridQuery(query, 'claude');
  }

  // File System Operations (ProtocolMutator)
  async mutateFileSystem(
    directory: string, 
    operation: 'analyze' | 'backup' | 'optimize' | 'sync',
    options: any = {}
  ): Promise<any> {
    const query = `Execute ProtocolMutator operation '${operation}' on directory '${directory}' with options: ${JSON.stringify(options)}`;
    return this.hybridQuery(query, 'claude');
  }

  async listDirectoryContents(directory: string): Promise<any[]> {
    const query = `List contents of directory: ${directory}`;
    const result = await this.hybridQuery(query, 'claude', {
      structured_output: true,
      output_schema: {
        type: 'object',
        properties: {
          files: { type: 'array' },
          directories: { type: 'array' },
          metadata: { type: 'object' }
        }
      }
    });

    return result.result.files || [];
  }

  // Code Generation
  async generateCodeFromVideo(
    videoTranscript: string,
    codeSegments: any[],
    targetLanguage: string = 'javascript'
  ): Promise<string> {
    const query = `Generate complete, functional ${targetLanguage} code based on video transcript and identified code segments. Transcript: ${videoTranscript}`;
    
    const result = await this.hybridQuery(query, 'grok', {
      structured_output: true,
      output_schema: {
        type: 'object',
        properties: {
          code: { type: 'string' },
          explanation: { type: 'string' },
          dependencies: { type: 'array' },
          setup_instructions: { type: 'string' }
        }
      }
    });

    return result.result.code;
  }

  // Real-time Analysis
  async performRealTimeAnalysis(topic: string, analysisType: 'trends' | 'sentiment' | 'market' = 'trends'): Promise<any> {
    try {
      const response = await fetch(this.bridgeUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          method: 'tools/call',
          params: {
            name: 'real_time_analysis',
            arguments: { topic, analysis_type: analysisType }
          }
        })
      });

      const result = await response.json();
      return result.result;
    } catch (error) {
      console.error('Real-time analysis failed:', error);
      throw error;
    }
  }

  // System Metrics
  async getSystemMetrics(): Promise<any> {
    try {
      const response = await fetch(this.bridgeUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          method: 'tools/call',
          params: {
            name: 'get_hybrid_metrics',
            arguments: {}
          }
        })
      });

      const result = await response.json();
      return result.result;
    } catch (error) {
      console.error('Failed to get system metrics:', error);
      return null;
    }
  }

  // Continuous Learning Integration
  async updateLearningModel(
    trainingData: any,
    modelType: 'video_processing' | 'code_generation' | 'skill_classification'
  ): Promise<any> {
    const query = `Update ${modelType} model with new training data. Implement incremental learning for improved performance.`;
    return this.hybridQuery(query, 'claude');
  }

  // State Continuity (ARM)
  async syncApplicationState(stateData: any): Promise<any> {
    const query = `Sync application state across devices using State Continuity Fabric: ${JSON.stringify(stateData)}`;
    return this.hybridQuery(query, 'claude');
  }

  // Quantum Computing Integration
  async optimizeWithQuantum(optimizationProblem: any): Promise<any> {
    const query = `Use quantum computing optimization for problem: ${JSON.stringify(optimizationProblem)}`;
    return this.hybridQuery(query, 'claude');
  }

  // Cleanup
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }
}

// React Hook for MCP Integration
export const useMCPIntegration = () => {
  const [service] = React.useState(() => new MCPIntegrationService());
  const [agentStatuses, setAgentStatuses] = React.useState<AgentStatus[]>([]);
  const [systemMetrics, setSystemMetrics] = React.useState(null);
  const [isConnected, setIsConnected] = React.useState(false);

  React.useEffect(() => {
    // Set up event listeners
    const handleAgentUpdate = (event: CustomEvent) => {
      setAgentStatuses(prev => {
        const updated = [...prev];
        const index = updated.findIndex(agent => agent.id === event.detail.id);
        if (index >= 0) {
          updated[index] = event.detail;
        } else {
          updated.push(event.detail);
        }
        return updated;
      });
    };

    window.addEventListener('agentStatusUpdate', handleAgentUpdate as EventListener);

    // Initial data load
    service.getAgentStatuses().then(setAgentStatuses);
    service.getSystemMetrics().then(setSystemMetrics);

    // Periodic updates
    const interval = setInterval(() => {
      service.getSystemMetrics().then(setSystemMetrics);
    }, 5000);

    return () => {
      window.removeEventListener('agentStatusUpdate', handleAgentUpdate as EventListener);
      clearInterval(interval);
      service.disconnect();
    };
  }, [service]);

  return {
    service,
    agentStatuses,
    systemMetrics,
    isConnected
  };
};

export default MCPIntegrationService;