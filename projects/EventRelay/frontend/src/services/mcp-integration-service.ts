/**
 * MCP Integration Service - Frontend
 * Connects React frontend to FastAPI backend
 */

import { useState, useEffect, useRef } from 'react';

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

export interface ChatMessage {
  id: string;
  sessionId: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: Date;
}

export class MCPIntegrationService {
  private apiUrl: string;
  private wsUrl: string;
  private socket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor() {
    // Get environment variables or use defaults
    this.apiUrl = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8010';
    this.wsUrl = process.env.REACT_APP_WS_URL || 'ws://127.0.0.1:8010/ws';
    this.initializeWebSocket();
  }

  private initializeWebSocket() {
    try {
      this.socket = new WebSocket(this.wsUrl);
      
      this.socket.onopen = () => {
        console.log('✅ Connected to backend WebSocket');
        this.reconnectAttempts = 0;
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleWebSocketMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.socket.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
      };

      this.socket.onclose = (event) => {
        console.log('🔌 WebSocket disconnected:', event.code, event.reason);
        this.handleReconnect();
      };

    } catch (error) {
      console.error('Error initializing WebSocket:', error);
    }
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`🔄 Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
      
      setTimeout(() => {
        this.initializeWebSocket();
      }, this.reconnectDelay * this.reconnectAttempts);
    } else {
      console.error('❌ Max reconnection attempts reached');
    }
  }

  private handleWebSocketMessage(data: any) {
    // Emit custom events for React components
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('backendMessage', { detail: data }));
      
      // Handle specific message types
      switch (data.type) {
        case 'connection':
          console.log('🔗 Backend connection established:', data.message);
          break;
        case 'chat_response':
          window.dispatchEvent(new CustomEvent('chatResponse', { detail: data }));
          break;
        case 'video_processing_response':
          window.dispatchEvent(new CustomEvent('videoProcessingResponse', { detail: data }));
          break;
        case 'error':
          console.error('❌ Backend error:', data.message);
          window.dispatchEvent(new CustomEvent('backendError', { detail: data }));
          break;
        default:
          console.log('📨 Received message:', data);
      }
    }
  }

  async sendChatMessage(message: string, context: string = 'tooltip-assistant'): Promise<any> {
    try {
      const response = await fetch(`${this.apiUrl}/api/chat`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ 
          message, 
          context,
          session_id: 'default'
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('✅ Chat response received:', data);
      return data;
    } catch (error) {
      console.error('❌ Error sending chat message:', error);
      throw error;
    }
  }

  async processVideo(videoUrl: string, options: any = {}): Promise<any> {
    try {
      const response = await fetch(`${this.apiUrl}/api/process-video`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ 
          video_url: videoUrl,
          options
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('✅ Video processing response received:', data);
      return data;
    } catch (error) {
      console.error('❌ Error processing video:', error);
      throw error;
    }
  }

  async checkHealth(): Promise<any> {
    try {
      const response = await fetch(`${this.apiUrl}/health`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('❌ Health check failed:', error);
      throw error;
    }
  }

  sendWebSocketMessage(message: any) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      try {
        this.socket.send(JSON.stringify(message));
        console.log('📤 WebSocket message sent:', message);
      } catch (error) {
        console.error('❌ Error sending WebSocket message:', error);
      }
    } else {
      console.warn('⚠️ WebSocket not connected, message not sent:', message);
    }
  }

  // WebSocket message helpers
  sendChatMessageWS(message: string, sessionId: string = 'default') {
    this.sendWebSocketMessage({
      type: 'chat',
      message,
      session_id: sessionId,
      timestamp: new Date().toISOString()
    });
  }

  sendVideoProcessingMessageWS(videoUrl: string, options: any = {}) {
    this.sendWebSocketMessage({
      type: 'video_processing',
      video_url: videoUrl,
      options,
      timestamp: new Date().toISOString()
    });
  }

  sendPing() {
    this.sendWebSocketMessage({
      type: 'ping',
      timestamp: new Date().toISOString()
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
      console.log('🔌 WebSocket disconnected');
    }
  }

  // Legacy methods for backward compatibility
  async hybridQuery(query: string, model: 'claude' | 'grok' | 'auto' = 'auto'): Promise<any> {
    return this.sendChatMessage(query);
  }

  async getAgentStatuses(): Promise<AgentStatus[]> {
    try {
      const health = await this.checkHealth();
      return [{
        id: 'backend',
        name: 'FastAPI Backend',
        status: health.status === 'healthy' ? 'active' : 'error',
        task: 'API Server',
        performance: {
          success_rate: 1.0,
          avg_response_time: 0,
          total_requests: 0
        }
      }];
    } catch (error) {
      return [{
        id: 'backend',
        name: 'FastAPI Backend',
        status: 'error',
        task: 'API Server',
        performance: {
          success_rate: 0.0,
          avg_response_time: 0,
          total_requests: 0
        }
      }];
    }
  }
}

// Export the service instance for direct use
export const mcpService = new MCPIntegrationService();

// React Hook for easy integration
export function useMCPIntegration() {
  const [isConnected, setIsConnected] = useState(false);
  const [messages] = useState<ChatMessage[]>([]);
  const serviceRef = useRef<MCPIntegrationService | null>(null);

  useEffect(() => {
    if (!serviceRef.current) {
      serviceRef.current = new MCPIntegrationService();
    }

    const checkConnection = async () => {
      try {
        if (serviceRef.current) {
          const health = await serviceRef.current.checkHealth();
          setIsConnected(health.status === 'healthy');
        }
      } catch {
        setIsConnected(false);
      }
    };

    checkConnection();
    const interval = setInterval(checkConnection, 5000);

    return () => {
      clearInterval(interval);
      if (serviceRef.current) {
        serviceRef.current.disconnect();
      }
    };
  }, []);

  const sendMessage = async (message: string) => {
    if (!serviceRef.current) return null;
    const response = await serviceRef.current.sendChatMessage(message);
    return response;
  };

  const processVideo = async (videoUrl: string, options?: any) => {
    if (!serviceRef.current) return null;
    const response = await serviceRef.current.processVideo(videoUrl, options);
    return response;
  };

  return {
    isConnected,
    messages,
    sendMessage,
    processVideo,
    service: serviceRef.current
  };
}
