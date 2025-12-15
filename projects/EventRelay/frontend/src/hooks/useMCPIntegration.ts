import { useState, useCallback, useRef, useEffect } from 'react';

// MCP Integration interfaces
export interface AgentStatus {
  id: string;
  name: string;
  status: 'idle' | 'busy' | 'error' | 'offline';
  lastSeen: Date;
  capabilities: string[];
  currentTask?: string;
  progress?: number;
  error?: string;
  metadata?: Record<string, any>;
}

export interface SystemMetrics {
  cpu: {
    usage: number;
    cores: number;
    temperature?: number;
  };
  memory: {
    total: number;
    used: number;
    available: number;
    usage: number;
  };
  disk: {
    total: number;
    used: number;
    available: number;
    usage: number;
  };
  network: {
    bytesIn: number;
    bytesOut: number;
    connections: number;
  };
  processes: {
    total: number;
    running: number;
    sleeping: number;
    stopped: number;
  };
  timestamp: Date;
}

export interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp: Date;
  metadata?: {
    tokens?: number;
    model?: string;
    processingTime?: number;
    confidence?: number;
    error?: boolean;
  };
}

export interface VideoProcessingOptions {
  quality: 'low' | 'medium' | 'high' | 'ultra';
  format: 'mp4' | 'webm' | 'avi' | 'mov';
  resolution?: string;
  fps?: number;
  bitrate?: number;
  includeTranscript?: boolean;
  includeChapters?: boolean;
  includeCodeExtraction?: boolean;
  includeSentimentAnalysis?: boolean;
  customPrompts?: string[];
}

export interface VideoProcessingResult {
  success: boolean;
  videoId: string;
  outputUrl?: string;
  transcript?: string;
  chapters?: any[];
  analysis?: any;
  metadata?: any;
  error?: string;
  processingTime?: number;
  fileSize?: number;
}

export interface MCPIntegrationState {
  isConnected: boolean;
  isConnecting: boolean;
  connectionError: string | null;
  agentStatuses: AgentStatus[];
  systemMetrics: SystemMetrics | null;
  messages: ChatMessage[];
  isProcessingVideo: boolean;
  videoProcessingProgress: number;
  currentVideoTask?: string;
  lastHealthCheck: Date | null;
  connectionRetries: number;
  maxRetries: number;
}

export interface MCPIntegrationOptions {
  autoReconnect?: boolean;
  reconnectDelay?: number;
  healthCheckInterval?: number;
  maxRetries?: number;
  enableLogging?: boolean;
  onConnectionChange?: (connected: boolean) => void;
  onAgentUpdate?: (agent: AgentStatus) => void;
  onSystemMetricsUpdate?: (metrics: SystemMetrics) => void;
  onVideoProcessingComplete?: (result: VideoProcessingResult) => void;
  onError?: (error: string) => void;
}

export const useMCPIntegration = (options: MCPIntegrationOptions = {}) => {
  const [state, setState] = useState<MCPIntegrationState>({
    isConnected: false,
    isConnecting: false,
    connectionError: null,
    agentStatuses: [],
    systemMetrics: null,
    messages: [],
    isProcessingVideo: false,
    videoProcessingProgress: 0,
    currentVideoTask: undefined,
    lastHealthCheck: null,
    connectionRetries: 0,
    maxRetries: 5,
  });

  const serviceRef = useRef<any>(null);
  const healthCheckIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const messageQueueRef = useRef<ChatMessage[]>([]);

  // Default options
  const defaultOptions: Required<MCPIntegrationOptions> = {
    autoReconnect: true,
    reconnectDelay: 5000,
    healthCheckInterval: 10000,
    maxRetries: 5,
    enableLogging: true,
    onConnectionChange: () => {},
    onAgentUpdate: () => {},
    onSystemMetricsUpdate: () => {},
    onVideoProcessingComplete: () => {},
    onError: () => {},
    ...options,
  };

  // Initialize MCP service
  const initializeService = useCallback(async () => {
    try {
      // Import the service dynamically to avoid SSR issues
      const { MCPIntegrationService } = await import('../services/mcp-integration-service');
      serviceRef.current = new MCPIntegrationService();
      
      // Set up event listeners
      if (serviceRef.current) {
        serviceRef.current.on('agentStatusUpdate', (agent: AgentStatus) => {
          setState(prev => {
            const updated = [...prev.agentStatuses];
            const index = updated.findIndex(a => a.id === agent.id);
            if (index >= 0) {
              updated[index] = agent;
            } else {
              updated.push(agent);
            }
            return { ...prev, agentStatuses: updated };
          });
          defaultOptions.onAgentUpdate(agent);
        });

        serviceRef.current.on('systemMetricsUpdate', (metrics: SystemMetrics) => {
          setState(prev => ({ ...prev, systemMetrics: metrics }));
          defaultOptions.onSystemMetricsUpdate(metrics);
        });

        serviceRef.current.on('videoProcessingComplete', (result: VideoProcessingResult) => {
          setState(prev => ({
            ...prev,
            isProcessingVideo: false,
            videoProcessingProgress: 100,
            currentVideoTask: undefined,
          }));
          defaultOptions.onVideoProcessingComplete(result);
        });

        serviceRef.current.on('error', (error: string) => {
          setState(prev => ({ ...prev, connectionError: error }));
          defaultOptions.onError(error);
        });
      }
    } catch (error) {
      console.error('Failed to initialize MCP service:', error);
      setState(prev => ({ 
        ...prev, 
        connectionError: 'Failed to initialize MCP service' 
      }));
    }
  }, [defaultOptions]);

  // Connect to MCP service
  const connect = useCallback(async () => {
    if (!serviceRef.current || state.isConnecting) return;

    setState(prev => ({ ...prev, isConnecting: true, connectionError: null }));

    try {
      const health = await serviceRef.current.checkHealth();
      
      if (health.status === 'healthy') {
        setState(prev => ({
          ...prev,
          isConnected: true,
          isConnecting: false,
          connectionError: null,
          connectionRetries: 0,
          lastHealthCheck: new Date(),
        }));
        
        defaultOptions.onConnectionChange(true);
        
        // Start health monitoring
        startHealthMonitoring();
        
        // Load initial data
        await Promise.all([
          loadAgentStatuses(),
          loadSystemMetrics(),
        ]);
        
        // Process queued messages
        processMessageQueue();
      } else {
        throw new Error(`Service unhealthy: ${health.status}`);
      }
    } catch (error: any) {
      const errorMessage = error.message || 'Connection failed';
      
      setState(prev => ({
        ...prev,
        isConnected: false,
        isConnecting: false,
        connectionError: errorMessage,
        connectionRetries: prev.connectionRetries + 1,
      }));
      
      defaultOptions.onConnectionChange(false);
      defaultOptions.onError(errorMessage);
      
      // Attempt reconnection if enabled
      if (defaultOptions.autoReconnect && state.connectionRetries < defaultOptions.maxRetries) {
        scheduleReconnect();
      }
    }
  }, [state.isConnecting, state.connectionRetries, defaultOptions]);

  // Disconnect from MCP service
  const disconnect = useCallback(() => {
    if (serviceRef.current) {
      serviceRef.current.disconnect();
    }
    
    // Clear intervals and timeouts
    if (healthCheckIntervalRef.current) {
      clearInterval(healthCheckIntervalRef.current);
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    setState(prev => ({
      ...prev,
      isConnected: false,
      isConnecting: false,
      connectionError: null,
      lastHealthCheck: null,
    }));
    
    defaultOptions.onConnectionChange(false);
  }, [defaultOptions]);

  // Start health monitoring
  const startHealthMonitoring = useCallback(() => {
    if (healthCheckIntervalRef.current) {
      clearInterval(healthCheckIntervalRef.current);
    }
    
    healthCheckIntervalRef.current = setInterval(async () => {
      if (!serviceRef.current || !state.isConnected) return;
      
      try {
        const health = await serviceRef.current.checkHealth();
        
        if (health.status === 'healthy') {
          setState(prev => ({ 
            ...prev, 
            lastHealthCheck: new Date(),
            connectionError: null 
          }));
        } else {
          throw new Error(`Service unhealthy: ${health.status}`);
        }
      } catch (error: any) {
        setState(prev => ({
          ...prev,
          isConnected: false,
          connectionError: error.message,
          lastHealthCheck: null,
        }));
        
        defaultOptions.onConnectionChange(false);
        
        // Attempt reconnection
        if (defaultOptions.autoReconnect) {
          scheduleReconnect();
        }
      }
    }, defaultOptions.healthCheckInterval);
  }, [state.isConnected, defaultOptions]);

  // Schedule reconnection
  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    reconnectTimeoutRef.current = setTimeout(() => {
      if (defaultOptions.enableLogging) {
        console.log(`Attempting to reconnect to MCP service (attempt ${state.connectionRetries + 1})`);
      }
      connect();
    }, defaultOptions.reconnectDelay);
  }, [defaultOptions, state.connectionRetries, connect]);

  // Load agent statuses
  const loadAgentStatuses = useCallback(async () => {
    if (!serviceRef.current) return;
    
    try {
      const agents = await serviceRef.current.getAgentStatuses();
      setState(prev => ({ ...prev, agentStatuses: agents }));
    } catch (error) {
      console.error('Failed to load agent statuses:', error);
    }
  }, []);

  // Load system metrics
  const loadSystemMetrics = useCallback(async () => {
    if (!serviceRef.current) return;
    
    try {
      const metrics = await serviceRef.current.getSystemMetrics();
      setState(prev => ({ ...prev, systemMetrics: metrics }));
    } catch (error) {
      console.error('Failed to load system metrics:', error);
    }
  }, []);

  // Send chat message
  const sendMessage = useCallback(async (content: string, metadata?: any) => {
    const message: ChatMessage = {
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      content,
      role: 'user',
      timestamp: new Date(),
      metadata,
    };

    // Add to messages
    setState(prev => ({ ...prev, messages: [...prev.messages, message] }));

    // Send immediately if connected
    if (state.isConnected && serviceRef.current) {
      try {
        const response = await serviceRef.current.sendChatMessage(content, metadata);
        
        if (response) {
          const assistantMessage: ChatMessage = {
            id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            content: response.content || response.message || 'Response received',
            role: 'assistant',
            timestamp: new Date(),
            metadata: response.metadata,
          };
          
          setState(prev => ({ ...prev, messages: [...prev.messages, assistantMessage] }));
        }
      } catch (error: any) {
        const errorMessage: ChatMessage = {
          id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          content: `Error: ${error.message}`,
          role: 'system',
          timestamp: new Date(),
          metadata: { error: true },
        };
        
        setState(prev => ({ ...prev, messages: [...prev.messages, errorMessage] }));
        defaultOptions.onError(error.message);
      }
    } else {
      // Queue message for later
      messageQueueRef.current.push(message);
    }

    return message;
  }, [state.isConnected, defaultOptions]);

  // Process message queue
  const processMessageQueue = useCallback(async () => {
    if (!state.isConnected || messageQueueRef.current.length === 0) return;
    
    const messages = [...messageQueueRef.current];
    messageQueueRef.current = [];
    
    for (const message of messages) {
      try {
        const response = await serviceRef.current.sendChatMessage(message.content, message.metadata);
        
        if (response) {
          const assistantMessage: ChatMessage = {
            id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            content: response.content || response.message || 'Response received',
            role: 'assistant',
            timestamp: new Date(),
            metadata: response.metadata,
          };
          
          setState(prev => ({ ...prev, messages: [...prev.messages, assistantMessage] }));
        }
      } catch (error: any) {
        console.error('Failed to process queued message:', error);
      }
    }
  }, [state.isConnected]);

  // Process video
  const processVideo = useCallback(async (
    videoUrl: string, 
    options: VideoProcessingOptions = {} as VideoProcessingOptions
  ) => {
    if (!serviceRef.current || !state.isConnected) {
      throw new Error('MCP service not connected');
    }

    setState(prev => ({
      ...prev,
      isProcessingVideo: true,
      videoProcessingProgress: 0,
      currentVideoTask: 'Initializing video processing...',
    }));

    try {
      // Start progress simulation
      let progress = 0;
      const progressInterval = setInterval(() => {
        progress += Math.random() * 10;
        if (progress < 90) {
          setState(prev => ({
            ...prev,
            videoProcessingProgress: Math.min(progress, 90),
            currentVideoTask: progress < 30 ? 'Analyzing video content...' :
                              progress < 60 ? 'Extracting transcript...' :
                              progress < 90 ? 'Processing analysis...' : 'Finalizing...',
          }));
        }
      }, 1000);

      const result = await serviceRef.current.processVideo(videoUrl, options);
      
      clearInterval(progressInterval);
      
      setState(prev => ({
        ...prev,
        isProcessingVideo: false,
        videoProcessingProgress: 100,
        currentVideoTask: 'Processing complete!',
      }));

      return result;
    } catch (error: any) {
      setState(prev => ({
        ...prev,
        isProcessingVideo: false,
        videoProcessingProgress: 0,
        currentVideoTask: undefined,
      }));
      
      throw error;
    }
  }, [state.isConnected]);

  // Get agent by ID
  const getAgentById = useCallback((agentId: string) => {
    return state.agentStatuses.find(agent => agent.id === agentId);
  }, [state.agentStatuses]);

  // Get agents by status
  const getAgentsByStatus = useCallback((status: AgentStatus['status']) => {
    return state.agentStatuses.filter(agent => agent.status === status);
  }, [state.agentStatuses]);

  // Get system health status
  const getSystemHealth = useCallback(() => {
    if (!state.systemMetrics) return 'unknown';
    
    const { cpu, memory, disk } = state.systemMetrics;
    
    if (cpu.usage > 90 || memory.usage > 90 || disk.usage > 90) {
      return 'critical';
    } else if (cpu.usage > 70 || memory.usage > 70 || disk.usage > 70) {
      return 'warning';
    } else if (cpu.usage > 50 || memory.usage > 50 || disk.usage > 50) {
      return 'moderate';
    } else {
      return 'healthy';
    }
  }, [state.systemMetrics]);

  // Clear messages
  const clearMessages = useCallback(() => {
    setState(prev => ({ ...prev, messages: [] }));
    messageQueueRef.current = [];
  }, []);

  // Initialize on mount
  useEffect(() => {
    initializeService();
    
    return () => {
      disconnect();
    };
  }, [initializeService, disconnect]);

  // Auto-connect when service is ready
  useEffect(() => {
    if (serviceRef.current && !state.isConnected && !state.isConnecting) {
      connect();
    }
  }, [serviceRef.current, state.isConnected, state.isConnecting, connect]);

  return {
    // State
    ...state,
    
    // Connection management
    connect,
    disconnect,
    
    // Messaging
    sendMessage,
    clearMessages,
    
    // Video processing
    processVideo,
    
    // Utilities
    getAgentById,
    getAgentsByStatus,
    getSystemHealth,
    
    // Service reference
    service: serviceRef.current,
  };
};
