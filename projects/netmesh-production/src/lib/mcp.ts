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
    // Use environment variables or default to localhost for dev
    private bridgeUrl = import.meta.env.VITE_MCP_BRIDGE_URL || 'http://localhost:8004/mcp';
    private orchestratorUrl = import.meta.env.VITE_ORCHESTRATOR_URL || 'http://localhost:8001';
    private socket: Socket | null = null;

    constructor() {
        this.initializeWebSocket();
    }

    private initializeWebSocket() {
        this.socket = io(this.orchestratorUrl, {
            transports: ['websocket'],
            autoConnect: true,
            reconnection: true,
            reconnectionAttempts: 5
        });

        this.socket.on('connect', () => {
            console.log('Connected to MCP orchestrator');
        });

        this.socket.on('connect_error', (err) => {
            console.warn('MCP orchestrator connection error', err);
        });

        this.socket.on('agent_status_update', (data: AgentStatus) => {
            window.dispatchEvent(new CustomEvent('agentStatusUpdate', { detail: data }));
        });

        this.socket.on('video_processing_progress', (data: any) => {
            window.dispatchEvent(new CustomEvent('videoProcessingProgress', { detail: data }));
        });
    }

    /**
     * Universal Hybrid Query
     * Routes requests to the "Master Node" backend
     */
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

            if (!response.ok) {
                throw new Error(`MCP Bridge Error: ${response.statusText}`);
            }

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

    /**
     * Process a YouTube Video via the backend Agent Swarm
     */
    async processYouTubeVideo(videoUrl: string): Promise<VideoProcessingResult> {
        const query = `Process YouTube video: ${videoUrl}. Extract transcript with timestamps, identify code segments, and analyze skill content.`;

        // We send this to the backend "Auto" model router
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

    // Cleanup
    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
    }
}

// React Hook
import { useState, useEffect } from 'react';

export const useMCPIntegration = () => {
    const [service] = useState(() => new MCPIntegrationService());
    const [agentStatuses, setAgentStatuses] = useState<AgentStatus[]>([]);
    const [isConnected, setIsConnected] = useState(false);

    useEffect(() => {
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
        // Note: Assuming socket connection logic sets isConnected state in a real impl

        return () => {
            window.removeEventListener('agentStatusUpdate', handleAgentUpdate as EventListener);
            service.disconnect();
        };
    }, [service]);

    return {
        service,
        agentStatuses,
        isConnected
    };
};

export default MCPIntegrationService;
