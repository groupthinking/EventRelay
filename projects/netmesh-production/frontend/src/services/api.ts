import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';
import { ErrorLogger } from './ErrorLogger';
import { ErrorReporter } from './ErrorReporter';

// API Configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const MCP_SERVER_URL = process.env.REACT_APP_MCP_SERVER_URL || 'http://localhost:3001';

// Error handling utilities
const errorLogger = new ErrorLogger();
const errorReporter = new ErrorReporter();

// Retry configuration
interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  retryCondition: (error: AxiosError) => boolean;
}

const defaultRetryConfig: RetryConfig = {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 10000,
  retryCondition: (error: AxiosError) => {
    const status = error.response?.status;
    return !status || status >= 500 || status === 429;
  }
};

// Circuit breaker for API endpoints
class CircuitBreaker {
  private failures: Map<string, number> = new Map();
  private lastFailure: Map<string, number> = new Map();
  private readonly threshold: number = 5;
  private readonly timeout: number = 60000; // 1 minute

  isOpen(endpoint: string): boolean {
    const failures = this.failures.get(endpoint) || 0;
    const lastFailure = this.lastFailure.get(endpoint) || 0;
    
    if (failures >= this.threshold) {
      if (Date.now() - lastFailure > this.timeout) {
        // Reset circuit breaker
        this.failures.set(endpoint, 0);
        return false;
      }
      return true;
    }
    return false;
  }

  recordFailure(endpoint: string): void {
    this.failures.set(endpoint, (this.failures.get(endpoint) || 0) + 1);
    this.lastFailure.set(endpoint, Date.now());
  }

  recordSuccess(endpoint: string): void {
    this.failures.set(endpoint, 0);
  }
}

const circuitBreaker = new CircuitBreaker();

// Enhanced axios request with retry, circuit breaker, and fallback
async function requestWithRetry(
  client: AxiosInstance,
  config: any,
  endpoint: string,
  retryConfig: RetryConfig = defaultRetryConfig,
  options: { allowFallback?: boolean; enableRateLimit?: boolean } = {}
): Promise<AxiosResponse> {
  const { allowFallback = true, enableRateLimit = true } = options;
  
  // Check rate limit
  if (enableRateLimit && !rateLimiter.canMakeRequest(endpoint)) {
    const waitTime = rateLimiter.getTimeUntilReset(endpoint);
    throw new Error(`Rate limit exceeded. Try again in ${Math.ceil(waitTime / 1000)} seconds.`);
  }
  
  // Check circuit breaker
  if (circuitBreaker.isOpen(endpoint)) {
    // Try to serve from fallback if available
    if (allowFallback) {
      const fallbackData = FallbackService.getFallbackData(endpoint);
      if (fallbackData) {
        errorLogger.info('Serving fallback data due to circuit breaker', { endpoint });
        return { data: fallbackData, status: 200 } as AxiosResponse;
      }
    }
    throw new Error(`Circuit breaker is open for ${endpoint}`);
  }

  let lastError: AxiosError | null = null;
  
  for (let attempt = 0; attempt <= retryConfig.maxRetries; attempt++) {
    try {
      const response = await client(config);
      circuitBreaker.recordSuccess(endpoint);
      
      // Store successful response as fallback data
      if (config.method?.toLowerCase() === 'get' && response.data) {
        FallbackService.storeFallbackData(endpoint, response.data);
      }
      
      return response;
    } catch (error) {
      lastError = error as AxiosError;
      
      // For network errors, try fallback before retrying
      if (allowFallback && !lastError.response && attempt === 0) {
        const fallbackData = FallbackService.getFallbackData(endpoint);
        if (fallbackData) {
          errorLogger.info('Using fallback data due to network error', { endpoint });
          return { data: fallbackData, status: 200 } as AxiosResponse;
        }
      }
      
      // Don't retry on last attempt
      if (attempt === retryConfig.maxRetries) {
        break;
      }
      
      // Check if we should retry
      if (!retryConfig.retryCondition(lastError)) {
        break;
      }
      
      // Calculate exponential backoff delay
      const delay = Math.min(
        retryConfig.baseDelay * Math.pow(2, attempt),
        retryConfig.maxDelay
      );
      
      // Add jitter to prevent thundering herd
      const jitteredDelay = delay + Math.random() * 1000;
      
      errorLogger.warn(`Retrying request to ${endpoint} in ${jitteredDelay}ms (attempt ${attempt + 1}/${retryConfig.maxRetries})`, {
        endpoint,
        attempt: attempt + 1,
        error: lastError.message
      });
      
      await new Promise(resolve => setTimeout(resolve, jitteredDelay));
    }
  }
  
  // All retries failed
  circuitBreaker.recordFailure(endpoint);
  
  // Final fallback attempt
  if (allowFallback) {
    const fallbackData = FallbackService.getFallbackData(endpoint);
    if (fallbackData) {
      errorLogger.warn('Using stale fallback data after all retries failed', { endpoint });
      return { data: fallbackData, status: 200 } as AxiosResponse;
    }
    
    // Queue request for later if it's a write operation
    if (config.method?.toLowerCase() !== 'get') {
      FallbackService.queueOfflineRequest(endpoint, config.data);
      errorLogger.info('Queued request for offline processing', { endpoint });
    }
  }
  
  throw lastError;
}

// Fallback service for graceful degradation
class FallbackService {
  private static fallbackData: Map<string, any> = new Map();
  private static offlineRequests: Array<{ endpoint: string; data: any; timestamp: number }> = [];

  static storeFallbackData(endpoint: string, data: any): void {
    this.fallbackData.set(endpoint, {
      data,
      timestamp: Date.now()
    });
    
    // Clean old data (older than 1 hour)
    const oneHourAgo = Date.now() - 3600000;
    for (const [key, value] of this.fallbackData.entries()) {
      if (value.timestamp < oneHourAgo) {
        this.fallbackData.delete(key);
      }
    }
  }

  static getFallbackData(endpoint: string): any | null {
    const cached = this.fallbackData.get(endpoint);
    if (cached && Date.now() - cached.timestamp < 3600000) { // 1 hour TTL
      return cached.data;
    }
    return null;
  }

  static queueOfflineRequest(endpoint: string, data: any): void {
    this.offlineRequests.push({
      endpoint,
      data,
      timestamp: Date.now()
    });
    
    // Limit queue size
    if (this.offlineRequests.length > 50) {
      this.offlineRequests.shift();
    }
  }

  static async processOfflineQueue(): Promise<void> {
    const requests = [...this.offlineRequests];
    this.offlineRequests = [];
    
    for (const request of requests) {
      try {
        // Attempt to replay request
        await apiClient.post(request.endpoint, request.data);
        errorLogger.info('Offline request processed successfully', { endpoint: request.endpoint });
      } catch (error) {
        errorLogger.warn('Failed to process offline request', error, { endpoint: request.endpoint });
      }
    }
  }
}

// Rate limiter for API requests
class RateLimiter {
  private requests: Map<string, number[]> = new Map();
  private readonly maxRequests = 100; // per minute
  private readonly windowMs = 60000; // 1 minute

  canMakeRequest(endpoint: string): boolean {
    const now = Date.now();
    const requests = this.requests.get(endpoint) || [];
    
    // Clean old requests
    const validRequests = requests.filter(time => now - time < this.windowMs);
    
    if (validRequests.length >= this.maxRequests) {
      return false;
    }
    
    validRequests.push(now);
    this.requests.set(endpoint, validRequests);
    return true;
  }

  getTimeUntilReset(endpoint: string): number {
    const requests = this.requests.get(endpoint) || [];
    if (requests.length === 0) return 0;
    
    const oldest = Math.min(...requests);
    return Math.max(0, this.windowMs - (Date.now() - oldest));
  }
}

const rateLimiter = new RateLimiter();

// Create axios instances with enhanced error handling
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

const mcpClient: AxiosInstance = axios.create({
  baseURL: MCP_SERVER_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for authentication and logging
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Add request ID for tracking
    const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    config.headers['X-Request-ID'] = requestId;
    
    // Log request
    errorLogger.debug(`API Request: ${config.method?.toUpperCase()} ${config.url}`, {
      requestId,
      method: config.method,
      url: config.url,
      data: config.data
    });
    
    return config;
  },
  (error) => {
    errorLogger.error('Request interceptor error', error);
    return Promise.reject(error);
  }
);

// Add request interceptor to MCP client too
mcpClient.interceptors.request.use(
  (config) => {
    const requestId = `mcp_req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    config.headers['X-Request-ID'] = requestId;
    
    errorLogger.debug(`MCP Request: ${config.method?.toUpperCase()} ${config.url}`, {
      requestId,
      method: config.method,
      url: config.url,
      data: config.data
    });
    
    return config;
  },
  (error) => Promise.reject(error)
);

// Enhanced response interceptor with comprehensive error handling
function createResponseInterceptor(clientName: string) {
  return {
    fulfilled: (response: AxiosResponse) => {
      errorLogger.debug(`${clientName} Response: ${response.status} ${response.config.url}`, {
        status: response.status,
        url: response.config.url,
        requestId: response.config.headers['X-Request-ID']
      });
      return response;
    },
    rejected: async (error: AxiosError) => {
      const requestId = error.config?.headers?.['X-Request-ID'];
      const endpoint = error.config?.url || 'unknown';
      
      // Create structured error data
      const errorData = {
        error: {
          name: error.name,
          message: error.message,
          stack: error.stack
        },
        context: {
          client: clientName,
          requestId,
          endpoint,
          method: error.config?.method,
          status: error.response?.status,
          statusText: error.response?.statusText,
          data: error.response?.data,
          timestamp: new Date().toISOString(),
          url: window.location.href,
          userAgent: navigator.userAgent
        },
        severity: determineErrorSeverity(error)
      };
      
      // Log the error
      errorLogger.error(`${clientName} Request Failed: ${endpoint}`, error, errorData);
      
      // Report critical errors
      if (errorData.severity === 'critical' || errorData.severity === 'high') {
        errorReporter.reportError({
          errorId: `api_error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          ...errorData,
          retryCount: 0
        });
      }
      
      // Handle specific error cases
      if (error.response?.status === 401) {
        errorLogger.warn('Unauthorized access - clearing auth token');
        localStorage.removeItem('auth_token');
        
        // Don't redirect in test environment
        if (process.env.NODE_ENV !== 'test') {
          window.location.href = '/login';
        }
      }
      
      // Handle rate limiting
      if (error.response?.status === 429) {
        const retryAfter = error.response.headers['retry-after'];
        errorLogger.warn(`Rate limited - retry after ${retryAfter}s`, { retryAfter });
      }
      
      // Enhance error with additional context
      const enhancedError = new Error(`${clientName} API Error: ${error.message}`);
      (enhancedError as any).originalError = error;
      (enhancedError as any).errorData = errorData;
      (enhancedError as any).isApiError = true;
      
      return Promise.reject(enhancedError);
    }
  };
}

// Determine error severity based on status code and error type
function determineErrorSeverity(error: AxiosError): 'low' | 'medium' | 'high' | 'critical' {
  const status = error.response?.status;
  
  if (!status) {
    // Network errors are high severity
    return 'high';
  }
  
  if (status >= 500) {
    return 'critical';
  }
  
  if (status === 429 || status === 408) {
    return 'medium';
  }
  
  if (status >= 400) {
    return status === 401 || status === 403 ? 'high' : 'medium';
  }
  
  return 'low';
}

// Apply response interceptors
const apiResponseInterceptor = createResponseInterceptor('API');
apiClient.interceptors.response.use(
  apiResponseInterceptor.fulfilled,
  apiResponseInterceptor.rejected
);

const mcpResponseInterceptor = createResponseInterceptor('MCP');
mcpClient.interceptors.response.use(
  mcpResponseInterceptor.fulfilled,
  mcpResponseInterceptor.rejected
);

// API Service Interfaces
export interface VideoAnalysisRequest {
  videoUrl: string;
  analysisType: 'basic' | 'comprehensive' | 'learning-focused';
  userId?: string;
}

export interface VideoAnalysisResponse {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  analysis?: any;
  error?: string;
  createdAt: string;
  updatedAt: string;
}

export interface MCPRequest {
  method: string;
  params: any;
  context?: any;
}

export interface MCPResponse {
  success: boolean;
  data?: any;
  error?: string;
  context?: any;
}

export interface GeminiCacheRequestPayload {
  contents: any;
  modelName?: string;
  ttlSeconds?: number;
  displayName?: string;
  generationParams?: Record<string, any>;
}

export interface GeminiCacheResponsePayload {
  success: boolean;
  cache?: Record<string, any>;
  error?: string;
  latency?: number;
}

export interface GeminiBatchRequestPayload {
  requests: Array<Record<string, any>>;
  modelName?: string;
  wait?: boolean;
  pollInterval?: number;
  timeout?: number;
  batchParams?: Record<string, any>;
}

export interface GeminiBatchResponsePayload {
  success: boolean;
  operation?: Record<string, any>;
  result?: any;
  completed?: boolean;
  error?: string;
  latency?: number;
}

export interface GeminiTokenRequestPayload {
  modelName?: string;
  audience?: string;
  ttlSeconds?: number;
  tokenParams?: Record<string, any>;
}

export interface GeminiTokenResponsePayload {
  success: boolean;
  token?: Record<string, any>;
  error?: string;
  latency?: number;
}

// Comprehensive health check and monitoring service
export class HealthService {
  private static healthHistory: Array<{ timestamp: number; health: any }> = [];
  private static isMonitoring = false;
  
  static async checkApiHealth(): Promise<{ status: string; latency: number; details?: any }> {
    const start = Date.now();
    try {
      const response = await apiClient.get('/health', { timeout: 5000 });
      const latency = Date.now() - start;
      return { 
        status: 'healthy', 
        latency,
        details: response.data
      };
    } catch (error) {
      const latency = Date.now() - start;
      return { 
        status: 'unhealthy', 
        latency,
        details: { error: (error as Error).message }
      };
    }
  }
  
  static async checkMcpHealth(): Promise<{ status: string; latency: number; details?: any }> {
    const start = Date.now();
    try {
      const response = await mcpClient.get('/health', { timeout: 5000 });
      const latency = Date.now() - start;
      return { 
        status: 'healthy', 
        latency,
        details: response.data
      };
    } catch (error) {
      const latency = Date.now() - start;
      return { 
        status: 'unhealthy', 
        latency,
        details: { error: (error as Error).message }
      };
    }
  }
  
  static async checkBrowserHealth(): Promise<{ status: string; details: any }> {
    const details: any = {
      userAgent: navigator.userAgent,
      language: navigator.language,
      onLine: navigator.onLine,
      cookieEnabled: navigator.cookieEnabled,
      localStorage: typeof(Storage) !== 'undefined',
      sessionStorage: typeof(Storage) !== 'undefined'
    };
    
    // Check memory if available
    if ('memory' in performance) {
      const memory = (performance as any).memory;
      details.memory = {
        usedJSHeapSize: memory.usedJSHeapSize,
        totalJSHeapSize: memory.totalJSHeapSize,
        jsHeapSizeLimit: memory.jsHeapSizeLimit,
        usagePercent: (memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100
      };
    }
    
    // Check connection if available
    if ('connection' in navigator) {
      const connection = (navigator as any).connection;
      details.connection = {
        effectiveType: connection.effectiveType,
        downlink: connection.downlink,
        rtt: connection.rtt,
        saveData: connection.saveData
      };
    }
    
    const status = navigator.onLine ? 'healthy' : 'offline';
    return { status, details };
  }
  
  static async performComprehensiveHealthCheck(): Promise<{
    api: { status: string; latency: number; details?: any };
    mcp: { status: string; latency: number; details?: any };
    browser: { status: string; details: any };
    circuitBreaker: { openEndpoints: string[]; failures: Record<string, number> };
    rateLimiter: { activeEndpoints: string[]; timeUntilReset: Record<string, number> };
    fallbackCache: { cachedEndpoints: string[]; queuedRequests: number };
    overall: string;
    score: number;
  }> {
    const [apiHealth, mcpHealth, browserHealth] = await Promise.all([
      this.checkApiHealth(),
      this.checkMcpHealth(),
      this.checkBrowserHealth()
    ]);
    
    // Get circuit breaker status
    const circuitBreakerStatus = {
      openEndpoints: Array.from((circuitBreaker as any).failures.keys()).filter(
        endpoint => circuitBreaker.isOpen(endpoint)
      ),
      failures: Object.fromEntries((circuitBreaker as any).failures.entries())
    };
    
    // Get rate limiter status
    const rateLimiterStatus = {
      activeEndpoints: Array.from((rateLimiter as any).requests.keys()),
      timeUntilReset: Object.fromEntries(
        Array.from((rateLimiter as any).requests.keys()).map(endpoint => [
          endpoint,
          rateLimiter.getTimeUntilReset(endpoint)
        ])
      )
    };
    
    // Get fallback cache status
    const fallbackStatus = {
      cachedEndpoints: Array.from((FallbackService as any).fallbackData.keys()),
      queuedRequests: (FallbackService as any).offlineRequests.length
    };
    
    // Calculate overall health score (0-100)
    let score = 100;
    if (apiHealth.status !== 'healthy') score -= 40;
    if (mcpHealth.status !== 'healthy') score -= 30;
    if (browserHealth.status !== 'healthy') score -= 20;
    if (circuitBreakerStatus.openEndpoints.length > 0) score -= 10;
    
    const overall = score >= 80 ? 'healthy' : score >= 60 ? 'degraded' : 'unhealthy';
    
    const healthCheck = {
      api: apiHealth,
      mcp: mcpHealth,
      browser: browserHealth,
      circuitBreaker: circuitBreakerStatus,
      rateLimiter: rateLimiterStatus,
      fallbackCache: fallbackStatus,
      overall,
      score
    };
    
    // Store in history
    this.healthHistory.push({ timestamp: Date.now(), health: healthCheck });
    
    // Keep only last 100 health checks
    if (this.healthHistory.length > 100) {
      this.healthHistory.shift();
    }
    
    return healthCheck;
  }
  
  static getHealthHistory(): Array<{ timestamp: number; health: any }> {
    return [...this.healthHistory];
  }
  
  static startHealthMonitoring(intervalMs: number = 30000): void {
    if (this.isMonitoring) return;
    
    this.isMonitoring = true;
    
    const monitor = async () => {
      if (!this.isMonitoring) return;
      
      try {
        const health = await this.performComprehensiveHealthCheck();
        
        // Process offline queue if API is healthy
        if (health.api.status === 'healthy') {
          await FallbackService.processOfflineQueue();
        }
        
        // Emit health update event
        window.dispatchEvent(new CustomEvent('health-update', { detail: health }));
        
      } catch (error) {
        errorLogger.error('Health monitoring error', error as Error);
      }
      
      setTimeout(monitor, intervalMs);
    };
    
    monitor();
  }
  
  static stopHealthMonitoring(): void {
    this.isMonitoring = false;
  }
}

// Main API Service with enhanced error handling
export class ApiService {
  // Video Analysis with enhanced error handling and progressive fallback
  static async analyzeVideo(request: VideoAnalysisRequest): Promise<VideoAnalysisResponse> {
    const endpoint = '/api/videos/analyze';
    
    try {
      const response = await requestWithRetry(
        apiClient,
        { method: 'post', url: endpoint, data: request },
        endpoint,
        defaultRetryConfig,
        { allowFallback: false } // No fallback for analysis requests
      );
      
      errorLogger.info('Video analysis completed successfully', {
        videoUrl: request.videoUrl,
        analysisType: request.analysisType,
        resultId: response.data.id
      });
      
      return response.data;
    } catch (error) {
      const errorMessage = `Video analysis failed: ${(error as Error).message}`;
      errorLogger.error(errorMessage, error as Error, { request });
      
      // Progressive degradation based on error type
      const originalError = (error as any)?.originalError;
      
      if (originalError?.response?.status === 400) {
        throw new Error('Invalid video URL or analysis parameters. Please check your input and try again.');
      }
      
      if (originalError?.response?.status === 413) {
        // Suggest alternative for large videos
        throw new Error('Video file is too large for analysis. Try with a shorter video or lower quality.');
      }
      
      if (originalError?.response?.status === 429) {
        throw new Error('Too many analysis requests. Please wait a moment before trying again.');
      }
      
      if (originalError?.response?.status === 503) {
        // Offer basic analysis as fallback
        if (request.analysisType !== 'basic') {
          errorLogger.info('Attempting fallback to basic analysis', { originalRequest: request });
          try {
            return await this.analyzeVideo({ ...request, analysisType: 'basic' });
          } catch (fallbackError) {
            // Continue to original error handling
          }
        }
        throw new Error('Analysis service is temporarily overloaded. Please try again in a few minutes.');
      }
      
      if (originalError?.code === 'ENOTFOUND' || originalError?.code === 'ECONNREFUSED') {
        throw new Error('Unable to connect to the analysis service. Please check your internet connection and try again.');
      }
      
      if (originalError?.code === 'TIMEOUT') {
        throw new Error('Analysis request timed out. This may be due to a large video file. Please try again or use a shorter video.');
      }
      
      // Generic fallback
      throw new Error(`Analysis failed: ${errorMessage}. Please try again later or contact support if the problem persists.`);
    }
  }

  static async getVideoAnalysis(id: string): Promise<VideoAnalysisResponse> {
    const endpoint = `/api/videos/analysis/${id}`;
    
    try {
      const response = await requestWithRetry(
        apiClient,
        { method: 'get', url: endpoint },
        endpoint
      );
      return response.data;
    } catch (error) {
      const errorMessage = `Failed to fetch video analysis: ${(error as Error).message}`;
      errorLogger.error(errorMessage, error as Error, { analysisId: id });
      
      if ((error as any)?.originalError?.response?.status === 404) {
        throw new Error('Video analysis not found. It may have been deleted or the ID is incorrect.');
      }
      
      throw new Error(errorMessage);
    }
  }

  static async getVideoList(): Promise<VideoAnalysisResponse[]> {
    const endpoint = '/api/videos/list';

    try {
      const response = await requestWithRetry(
        apiClient,
        { method: 'get', url: endpoint },
        endpoint,
        defaultRetryConfig,
        { allowFallback: true } // Enable fallback for read operations
      );
      return response.data;
    } catch (error) {
      const errorMessage = `Failed to fetch video list: ${(error as Error).message}`;
      errorLogger.error(errorMessage, error as Error);

      // Check for cached data first
      const cachedData = FallbackService.getFallbackData(endpoint);
      if (cachedData) {
        errorLogger.info('Using cached video list due to API error');
        return cachedData;
      }

      // Return empty array for graceful degradation
      errorLogger.warn('API unavailable and no cached data - returning empty video list for graceful degradation');
      return [];
    }
  }

  static async requestEphemeralToken(
    params: GeminiTokenRequestPayload
  ): Promise<GeminiTokenResponsePayload> {
    const endpoint = '/api/v1/hybrid/ephemeral-token';

    const payload: Record<string, any> = {};
    if (params.modelName) payload.model_name = params.modelName;
    if (params.audience) payload.audience = params.audience;
    if (typeof params.ttlSeconds === 'number') payload.ttl_seconds = params.ttlSeconds;
    if (params.tokenParams && Object.keys(params.tokenParams).length) {
      payload.token_params = params.tokenParams;
    }

    try {
      const response = await requestWithRetry(
        apiClient,
        { method: 'post', url: endpoint, data: payload },
        endpoint,
        { ...defaultRetryConfig, maxRetries: 1 }
      );
      return response.data as GeminiTokenResponsePayload;
    } catch (error) {
      const errorMessage = `Failed to create ephemeral token: ${(error as Error).message}`;
      errorLogger.error(errorMessage, error as Error, { params });
      throw new Error(errorMessage);
    }
  }

  static async createHybridCache(
    params: GeminiCacheRequestPayload
  ): Promise<GeminiCacheResponsePayload> {
    const endpoint = '/api/v1/hybrid/cache';

    const payload: Record<string, any> = {
      contents: params.contents,
    };

    if (params.modelName) payload.model_name = params.modelName;
    if (typeof params.ttlSeconds === 'number') payload.ttl_seconds = params.ttlSeconds;
    if (params.displayName) payload.display_name = params.displayName;
    if (params.generationParams && Object.keys(params.generationParams).length) {
      payload.generation_params = params.generationParams;
    }

    try {
      const response = await requestWithRetry(
        apiClient,
        { method: 'post', url: endpoint, data: payload },
        endpoint
      );
      return response.data as GeminiCacheResponsePayload;
    } catch (error) {
      const errorMessage = `Failed to create Gemini cache: ${(error as Error).message}`;
      errorLogger.error(errorMessage, error as Error, { params });
      throw new Error(errorMessage);
    }
  }

  static async submitHybridBatch(
    params: GeminiBatchRequestPayload
  ): Promise<GeminiBatchResponsePayload> {
    const endpoint = '/api/v1/hybrid/batch';

    const payload: Record<string, any> = {
      requests: params.requests,
    };

    if (params.modelName) payload.model_name = params.modelName;
    if (typeof params.wait === 'boolean') payload.wait = params.wait;
    if (typeof params.pollInterval === 'number') payload.poll_interval = params.pollInterval;
    if (typeof params.timeout === 'number') payload.timeout = params.timeout;
    if (params.batchParams && Object.keys(params.batchParams).length) {
      payload.batch_params = params.batchParams;
    }

    try {
      const response = await requestWithRetry(
        apiClient,
        { method: 'post', url: endpoint, data: payload },
        endpoint,
        { ...defaultRetryConfig, maxRetries: 1 },
      );
      return response.data as GeminiBatchResponsePayload;
    } catch (error) {
      const errorMessage = `Failed to submit Gemini batch job: ${(error as Error).message}`;
      errorLogger.error(errorMessage, error as Error, { params });
      throw new Error(errorMessage);
    }
  }

  // MCP Integration with enhanced error handling and intelligent fallbacks
  static async sendMCPRequest(request: MCPRequest): Promise<MCPResponse> {
    const endpoint = '/mcp/request';
    
    try {
      const response = await requestWithRetry(
        mcpClient,
        { method: 'post', url: endpoint, data: request },
        endpoint,
        { ...defaultRetryConfig, maxRetries: 2 }, // Fewer retries for MCP
        { allowFallback: true }
      );
      
      errorLogger.info('MCP request completed successfully', {
        method: request.method,
        success: response.data.success
      });
      
      return response.data;
    } catch (error) {
      const errorMessage = `MCP request failed: ${(error as Error).message}`;
      errorLogger.error(errorMessage, error as Error, { request });
      
      // Implement method-specific fallbacks
      if (request.method === 'get_capabilities') {
        return {
          success: true,
          data: {
            capabilities: ['basic'], // Minimal capabilities when MCP is down
            version: 'fallback'
          },
          context: { fallback: true, message: 'Using basic capabilities while MCP is unavailable' }
        };
      }
      
      if (request.method === 'process_video' && request.params?.fallback_enabled) {
        // Attempt basic processing without MCP
        return {
          success: false,
          error: 'Advanced processing unavailable. Basic analysis may still be possible.',
          data: { suggested_action: 'Try basic analysis instead' },
          context: { fallback: true, retry_suggested: true }
        };
      }
      
      // Generic graceful degradation
      return {
        success: false,
        error: 'MCP service is temporarily unavailable. Some advanced features may be limited.',
        context: { 
          fallback: true, 
          error_code: 'MCP_UNAVAILABLE',
          retry_after: 60 // Suggest retry after 1 minute
        }
      };
    }
  }

  static async getMCPStatus(): Promise<{ status: string; version: string }> {
    const endpoint = '/mcp/status';
    
    try {
      const response = await requestWithRetry(
        mcpClient,
        { method: 'get', url: endpoint },
        endpoint,
        { ...defaultRetryConfig, maxRetries: 1 } // Single retry for status check
      );
      return response.data;
    } catch (error) {
      const errorMessage = `Failed to get MCP status: ${(error as Error).message}`;
      errorLogger.error(errorMessage, error as Error);
      
      // Return degraded status instead of throwing
      return {
        status: 'unavailable',
        version: 'unknown'
      };
    }
  }

  // Learning Fusion
  static async generateLearningPath(videoId: string, learningStyle: string): Promise<any> {
    try {
      const response = await apiClient.post('/api/learning/generate-path', {
        videoId,
        learningStyle,
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to generate learning path: ${error}`);
    }
  }

  // User Management
  static async getUserProfile(): Promise<any> {
    try {
      const response = await apiClient.get('/api/user/profile');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch user profile: ${error}`);
    }
  }

  static async updateUserProfile(profile: any): Promise<any> {
    try {
      const response = await apiClient.put('/api/user/profile', profile);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to update user profile: ${error}`);
    }
  }
}

// Initialize health monitoring on module load
if (typeof window !== 'undefined') {
  // Start health monitoring after a short delay
  setTimeout(() => {
    HealthService.startHealthMonitoring();
  }, 1000);
  
  // Listen for network status changes
  window.addEventListener('online', () => {
    errorLogger.info('Network connection restored');
    // Process offline queue immediately
    FallbackService.processOfflineQueue();
  });
  
  window.addEventListener('offline', () => {
    errorLogger.warn('Network connection lost - entering offline mode');
  });
  
  // Cleanup on page unload
  window.addEventListener('beforeunload', () => {
    HealthService.stopHealthMonitoring();
  });
}

// Export everything
export { FallbackService, RateLimiter, circuitBreaker, rateLimiter };
export default ApiService;
