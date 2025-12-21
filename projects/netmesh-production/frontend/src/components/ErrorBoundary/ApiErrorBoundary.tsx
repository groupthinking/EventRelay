import React, { Component, ErrorInfo, ReactNode } from 'react';
import { ErrorReporter } from '../../services/ErrorReporter';
import { ErrorLogger } from '../../services/ErrorLogger';

interface Props {
  children: ReactNode;
  apiName?: string;
  fallback?: ReactNode;
  retryEnabled?: boolean;
  showUserFriendlyMessage?: boolean;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
  errorId?: string;
  retryCount: number;
  isRetrying: boolean;
  apiErrors: ApiErrorInfo[];
}

interface ApiErrorInfo {
  timestamp: string;
  endpoint?: string;
  method?: string;
  status?: number;
  message: string;
  retryAfter?: number;
}

/**
 * ApiErrorBoundary - Specialized error boundary for API-related failures
 * 
 * Features:
 * - API-specific error handling and categorization
 * - Intelligent retry logic with backoff
 * - Network error detection and recovery
 * - Rate limiting and quota handling
 * - User-friendly API error messages
 */
export class ApiErrorBoundary extends Component<Props, State> {
  private errorReporter: ErrorReporter;
  private errorLogger: ErrorLogger;
  private retryTimer?: NodeJS.Timeout;
  private readonly MAX_RETRY_ATTEMPTS = 3;

  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      retryCount: 0,
      isRetrying: false,
      apiErrors: []
    };
    
    this.errorReporter = new ErrorReporter();
    this.errorLogger = new ErrorLogger();
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
      errorId: `API_ERR_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    };
  }

  async componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const { apiName = 'unknown' } = this.props;
    
    const apiErrorInfo = this.parseApiError(error);
    const errorContext = {
      level: 'api',
      errorId: this.state.errorId!,
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack
      },
      errorInfo: {
        componentStack: errorInfo.componentStack
      },
      context: {
        apiName,
        url: window.location.href,
        userAgent: navigator.userAgent,
        timestamp: new Date().toISOString(),
        userId: this.getUserId(),
        sessionId: this.getSessionId(),
        retryCount: this.state.retryCount,
        apiError: apiErrorInfo,
        networkInfo: this.getNetworkInfo()
      },
      severity: this.determineSeverity(error, apiErrorInfo),
      retryCount: this.state.retryCount,
      tags: this.generateApiErrorTags(error, apiErrorInfo)
    };

    // Log API error with context
    this.errorLogger.error(`API Error in ${apiName}`, error, errorContext);
    
    // Report to monitoring service
    try {
      await this.errorReporter.reportError(errorContext);
    } catch (reportingError) {
      console.warn('Failed to report API error:', reportingError);
    }

    // Update state with API error info
    this.setState({ 
      error, 
      errorInfo,
      apiErrors: [...this.state.apiErrors, {
        timestamp: new Date().toISOString(),
        ...apiErrorInfo
      }].slice(-5) // Keep last 5 errors
    });
    
    // Auto-retry for recoverable API errors
    if (this.isRetryableError(error, apiErrorInfo) && this.state.retryCount < this.MAX_RETRY_ATTEMPTS) {
      this.scheduleRetry(apiErrorInfo.retryAfter);
    }
  }

  private parseApiError(error: Error): ApiErrorInfo {
    const errorInfo: ApiErrorInfo = {
      timestamp: new Date().toISOString(),
      message: error.message
    };

    // Parse fetch errors
    if (error.message.includes('fetch')) {
      const urlMatch = error.message.match(/fetch\s+(.+?)(?:\s|$)/);
      if (urlMatch) {
        try {
          const url = new URL(urlMatch[1]);
          errorInfo.endpoint = url.pathname;
        } catch (e) {
          errorInfo.endpoint = urlMatch[1];
        }
      }
    }

    // Parse HTTP status errors
    const statusMatch = error.message.match(/(\d{3})/);
    if (statusMatch) {
      errorInfo.status = parseInt(statusMatch[1]);
    }

    // Parse method from error stack or message
    const methodMatch = error.message.match(/(GET|POST|PUT|DELETE|PATCH)/i);
    if (methodMatch) {
      errorInfo.method = methodMatch[1].toUpperCase();
    }

    // Parse retry-after header value
    const retryMatch = error.message.match(/retry[^\d]*(\d+)/i);
    if (retryMatch) {
      errorInfo.retryAfter = parseInt(retryMatch[1]) * 1000; // Convert to milliseconds
    }

    return errorInfo;
  }

  private isRetryableError(error: Error, apiInfo: ApiErrorInfo): boolean {
    // Network errors
    if (error.name === 'NetworkError' || error.message.includes('fetch')) {
      return true;
    }

    // Specific HTTP status codes that are retryable
    if (apiInfo.status) {
      return [408, 429, 500, 502, 503, 504].includes(apiInfo.status);
    }

    // Timeout errors
    if (error.name === 'TimeoutError' || error.message.includes('timeout')) {
      return true;
    }

    // Service unavailable patterns
    return /service.*unavailable|server.*error|connection.*reset/i.test(error.message);
  }

  private scheduleRetry(retryAfter?: number) {
    this.setState({ isRetrying: true });
    
    // Calculate retry delay with exponential backoff
    const baseDelay = retryAfter || (1000 * Math.pow(2, this.state.retryCount)); // 1s, 2s, 4s
    const jitterDelay = baseDelay + (Math.random() * 1000); // Add jitter
    
    this.retryTimer = setTimeout(() => {
      this.setState({
        hasError: false,
        error: undefined,
        errorInfo: undefined,
        retryCount: this.state.retryCount + 1,
        isRetrying: false
      });
      
      this.errorLogger.info(`API retry attempt ${this.state.retryCount + 1}`, {
        delay: jitterDelay,
        apiName: this.props.apiName
      });
    }, jitterDelay);
  }

  private determineSeverity(error: Error, apiInfo: ApiErrorInfo): 'low' | 'medium' | 'high' | 'critical' {
    // Critical: Auth failures, permanent errors
    if (apiInfo.status && [401, 403].includes(apiInfo.status)) {
      return 'critical';
    }
    
    // High: Client errors that won't retry
    if (apiInfo.status && [400, 404, 422].includes(apiInfo.status)) {
      return 'high';
    }
    
    // Medium: Server errors that might recover
    if (apiInfo.status && [500, 502, 503].includes(apiInfo.status)) {
      return 'medium';
    }
    
    // Low: Network/temporary issues
    return 'low';
  }

  private generateApiErrorTags(error: Error, apiInfo: ApiErrorInfo): string[] {
    const tags = ['api-error'];
    
    if (this.props.apiName) {
      tags.push(`api:${this.props.apiName.toLowerCase()}`);
    }
    
    if (apiInfo.status) {
      tags.push(`status:${apiInfo.status}`);
      tags.push(`status-class:${Math.floor(apiInfo.status / 100)}xx`);
    }
    
    if (apiInfo.method) {
      tags.push(`method:${apiInfo.method.toLowerCase()}`);
    }
    
    if (apiInfo.endpoint) {
      tags.push(`endpoint:${apiInfo.endpoint.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase()}`);
    }
    
    if (error.name === 'NetworkError') {
      tags.push('network-error');
    }
    
    return tags;
  }

  private getUserId(): string {
    return localStorage.getItem('userId') || 'anonymous';
  }

  private getSessionId(): string {
    let sessionId = sessionStorage.getItem('sessionId');
    if (!sessionId) {
      sessionId = `api_session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('sessionId', sessionId);
    }
    return sessionId;
  }

  private getNetworkInfo(): any {
    try {
      const connection = (navigator as any).connection;
      return connection ? {
        effectiveType: connection.effectiveType,
        downlink: connection.downlink,
        rtt: connection.rtt,
        saveData: connection.saveData
      } : null;
    } catch (error) {
      return null;
    }
  }

  private getErrorMessage(error: Error, apiInfo: ApiErrorInfo): {
    title: string;
    description: string;
    userAction: string;
    technical?: string;
  } {
    const { showUserFriendlyMessage = true } = this.props;
    
    // Authentication errors
    if (apiInfo.status === 401) {
      return {
        title: 'Authentication Required',
        description: 'Your session has expired. Please log in again to continue.',
        userAction: 'Click "Sign In" to authenticate and retry your request.',
        technical: showUserFriendlyMessage ? undefined : `HTTP 401: ${error.message}`
      };
    }
    
    // Permission errors  
    if (apiInfo.status === 403) {
      return {
        title: 'Access Denied',
        description: 'You don\'t have permission to access this resource.',
        userAction: 'Contact support if you believe this is an error.',
        technical: showUserFriendlyMessage ? undefined : `HTTP 403: ${error.message}`
      };
    }
    
    // Rate limiting
    if (apiInfo.status === 429) {
      return {
        title: 'Too Many Requests',
        description: 'You\'re sending requests too quickly. Please wait a moment before trying again.',
        userAction: `Wait ${Math.ceil((apiInfo.retryAfter || 60000) / 1000)} seconds and try again.`,
        technical: showUserFriendlyMessage ? undefined : `HTTP 429: Rate limit exceeded`
      };
    }
    
    // Server errors
    if (apiInfo.status && apiInfo.status >= 500) {
      return {
        title: 'Service Temporarily Unavailable',
        description: 'Our servers are experiencing temporary issues. We\'re working to resolve this quickly.',
        userAction: 'Please try again in a few moments. If the problem persists, contact support.',
        technical: showUserFriendlyMessage ? undefined : `HTTP ${apiInfo.status}: ${error.message}`
      };
    }
    
    // Network errors
    if (error.name === 'NetworkError' || error.message.includes('fetch')) {
      return {
        title: 'Connection Problem',
        description: 'Unable to connect to our servers. Please check your internet connection.',
        userAction: 'Verify your internet connection and try again.',
        technical: showUserFriendlyMessage ? undefined : `Network Error: ${error.message}`
      };
    }
    
    // Generic API error
    return {
      title: 'Service Error',
      description: 'We encountered an issue processing your request.',
      userAction: 'Please try again. If the problem continues, contact support.',
      technical: showUserFriendlyMessage ? undefined : error.message
    };
  }

  private handleRetry = () => {
    this.setState({
      hasError: false,
      error: undefined,
      errorInfo: undefined,
      retryCount: this.state.retryCount + 1
    });
  };

  private handleRefresh = () => {
    window.location.reload();
  };

  componentWillUnmount() {
    if (this.retryTimer) {
      clearTimeout(this.retryTimer);
    }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      if (this.state.isRetrying) {
        return this.renderRetrying();
      }

      return this.renderApiError();
    }

    return this.props.children;
  }

  private renderRetrying() {
    const { apiName = 'API' } = this.props;
    
    return (
      <div className="flex items-center justify-center p-8 bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-lg">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-blue-800 dark:text-blue-200 font-medium">
            Retrying {apiName} request...
          </p>
          <p className="text-sm text-blue-600 dark:text-blue-400 mt-1">
            Attempt {this.state.retryCount + 1} of {this.MAX_RETRY_ATTEMPTS}
          </p>
        </div>
      </div>
    );
  }

  private renderApiError() {
    const { apiName = 'API', retryEnabled = true } = this.props;
    const canRetry = retryEnabled && this.state.retryCount < this.MAX_RETRY_ATTEMPTS;
    const errorMessage = this.getErrorMessage(this.state.error!, this.parseApiError(this.state.error!));
    
    return (
      <div className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-lg p-6">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="w-6 h-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          
          <div className="ml-3 flex-1">
            <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
              {errorMessage.title}
            </h3>
            
            <p className="mt-2 text-sm text-red-700 dark:text-red-300">
              {errorMessage.description}
            </p>
            
            <p className="mt-2 text-sm text-red-600 dark:text-red-400">
              {errorMessage.userAction}
            </p>
            
            {this.state.errorId && (
              <p className="mt-2 text-xs text-red-500 dark:text-red-500">
                Error ID: {this.state.errorId}
              </p>
            )}
            
            <div className="mt-4 flex flex-wrap gap-2">
              {canRetry && (
                <button
                  onClick={this.handleRetry}
                  className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                >
                  Try Again
                </button>
              )}
              
              <button
                onClick={this.handleRefresh}
                className="inline-flex items-center px-3 py-2 border border-red-300 dark:border-red-700 text-sm leading-4 font-medium rounded-md text-red-700 dark:text-red-300 bg-white dark:bg-red-900/20 hover:bg-red-50 dark:hover:bg-red-900/30 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                Refresh Page
              </button>
            </div>
            
            {/* Development details */}
            {(process.env.NODE_ENV === 'development' || errorMessage.technical) && (
              <details className="mt-4">
                <summary className="text-xs text-red-600 dark:text-red-400 cursor-pointer hover:text-red-800 dark:hover:text-red-200">
                  Technical Details
                </summary>
                <div className="mt-2 p-2 bg-red-100 dark:bg-red-900/20 rounded text-xs font-mono text-red-800 dark:text-red-200 overflow-auto">
                  {errorMessage.technical && (
                    <div className="mb-2">
                      <strong>Error:</strong> {errorMessage.technical}
                    </div>
                  )}
                  <div className="mb-2">
                    <strong>API:</strong> {apiName}
                  </div>
                  <div className="mb-2">
                    <strong>Retry Count:</strong> {this.state.retryCount}
                  </div>
                  {this.state.apiErrors.length > 0 && (
                    <div>
                      <strong>Recent API Errors:</strong>
                      {this.state.apiErrors.map((apiError, index) => (
                        <div key={index} className="ml-2 mt-1 text-xs">
                          {new Date(apiError.timestamp).toLocaleTimeString()}: 
                          {apiError.status && ` ${apiError.status}`}
                          {apiError.method && ` ${apiError.method}`}
                          {apiError.endpoint && ` ${apiError.endpoint}`}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </details>
            )}
          </div>
        </div>
      </div>
    );
  }
}