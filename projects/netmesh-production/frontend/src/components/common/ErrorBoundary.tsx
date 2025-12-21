import React, { Component, ErrorInfo, ReactNode } from 'react';
import { ErrorReporter } from '../../services/ErrorReporter';
import { ErrorLogger } from '../../services/ErrorLogger';

export interface ErrorBoundaryLevel {
  GLOBAL: 'global';
  COMPONENT: 'component';
  FEATURE: 'feature';
}

export interface ErrorAction {
  label: string;
  action: () => void;
  primary?: boolean;
}

interface Props {
  children: ReactNode;
  level?: 'global' | 'component' | 'feature';
  fallback?: ReactNode;
  showReload?: boolean;
  showRetry?: boolean;
  customActions?: ErrorAction[];
  context?: Record<string, any>;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  isolate?: boolean;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
  errorId?: string;
  retryCount: number;
  isRecovering: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  private errorReporter: ErrorReporter;
  private errorLogger: ErrorLogger;
  private retryTimer?: NodeJS.Timeout;

  constructor(props: Props) {
    super(props);
    this.state = { 
      hasError: false,
      retryCount: 0,
      isRecovering: false
    };
    
    this.errorReporter = new ErrorReporter();
    this.errorLogger = new ErrorLogger();
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { 
      hasError: true, 
      error,
      errorId: `ERR_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    };
  }

  async componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const { level = 'component', context = {}, onError } = this.props;
    
    // Enhanced error logging with context
    const errorData = {
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack
      },
      errorInfo: {
        componentStack: errorInfo.componentStack
      },
      context: {
        level,
        userAgent: navigator.userAgent,
        url: window.location.href,
        timestamp: new Date().toISOString(),
        userId: this.getUserId(),
        sessionId: this.getSessionId(),
        ...context
      },
      severity: this.determineSeverity(error, level),
      retryCount: this.state.retryCount
    };

    // Log error with structured data
    this.errorLogger.logError(errorData);
    
    // Report to monitoring service
    try {
      await this.errorReporter.reportError({
        errorId: this.state.errorId!,
        ...errorData
      });
    } catch (reportingError) {
      console.warn('Failed to report error:', reportingError);
    }

    this.setState({ error, errorInfo });
    
    // Call custom error handler
    onError?.(error, errorInfo);
    
    // Auto-retry for transient errors
    if (this.isTransientError(error) && this.state.retryCount < 3) {
      this.scheduleRetry();
    }
  }

  private getUserId(): string {
    return localStorage.getItem('userId') || 'anonymous';
  }

  private getSessionId(): string {
    let sessionId = sessionStorage.getItem('sessionId');
    if (!sessionId) {
      sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('sessionId', sessionId);
    }
    return sessionId;
  }

  private determineSeverity(error: Error, level: string): 'low' | 'medium' | 'high' | 'critical' {
    if (level === 'global') return 'critical';
    if (error.name === 'ChunkLoadError') return 'medium';
    if (error.message.includes('Network')) return 'medium';
    return 'high';
  }

  private isTransientError(error: Error): boolean {
    const transientPatterns = [
      /ChunkLoadError/,
      /Loading chunk \d+ failed/,
      /NetworkError/,
      /fetch/
    ];
    return transientPatterns.some(pattern => pattern.test(error.message));
  }

  private scheduleRetry = () => {
    this.setState({ isRecovering: true });
    
    this.retryTimer = setTimeout(() => {
      this.setState({
        hasError: false,
        error: undefined,
        errorInfo: undefined,
        retryCount: this.state.retryCount + 1,
        isRecovering: false
      });
    }, Math.pow(2, this.state.retryCount) * 1000); // Exponential backoff
  };

  private handleRetry = () => {
    this.setState({
      hasError: false,
      error: undefined,
      errorInfo: undefined,
      retryCount: this.state.retryCount + 1
    });
  };

  private handleReload = () => {
    window.location.reload();
  };

  private getErrorMessage(error: Error): { title: string; description: string; userAction: string } {
    if (error.name === 'ChunkLoadError') {
      return {
        title: 'Loading Issue',
        description: 'There was a problem loading part of the application. This usually happens after an update.',
        userAction: 'Please refresh the page to get the latest version.'
      };
    }
    
    if (error.message.includes('Network')) {
      return {
        title: 'Connection Problem', 
        description: 'Unable to connect to our servers. Please check your internet connection.',
        userAction: 'Try again in a moment or refresh the page.'
      };
    }

    return {
      title: 'Unexpected Error',
      description: 'Something unexpected happened. Our team has been notified.',
      userAction: 'You can try again or refresh the page.'
    };
  }

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

      if (this.state.isRecovering) {
        return this.renderRecovering();
      }

      const { level = 'component' } = this.props;
      const errorMessage = this.getErrorMessage(this.state.error!);
      
      return this.renderErrorUI(errorMessage, level);
    }

    return this.props.children;
  }

  private renderRecovering() {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Recovering...</p>
        </div>
      </div>
    );
  }

  private renderErrorUI(errorMessage: { title: string; description: string; userAction: string }, level: string) {
    const isGlobal = level === 'global';
    const containerClass = isGlobal 
      ? "min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4"
      : "bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-lg p-6 my-4";
    
    const maxWidthClass = isGlobal ? "max-w-md" : "max-w-full";

    return (
      <div className={containerClass}>
        <div className={`${maxWidthClass} w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 text-center`}>
          <div className="w-16 h-16 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            {errorMessage.title}
          </h2>
          
          <p className="text-gray-600 dark:text-gray-400 mb-2">
            {errorMessage.description}
          </p>
          
          <p className="text-sm text-gray-500 dark:text-gray-500 mb-4">
            {errorMessage.userAction}
          </p>

          {this.state.errorId && (
            <p className="text-xs text-gray-400 dark:text-gray-600 mb-4">
              Error ID: {this.state.errorId}
            </p>
          )}

          <div className="space-y-3">
            {this.props.showRetry !== false && (
              <button
                onClick={this.handleRetry}
                className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
              >
                Try Again
              </button>
            )}
            
            {this.props.showReload !== false && (
              <button
                onClick={this.handleReload}
                className="w-full bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-4 py-2 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
              >
                {isGlobal ? 'Refresh Page' : 'Reload Component'}
              </button>
            )}
            
            {this.props.customActions?.map((action, index) => (
              <button
                key={index}
                onClick={action.action}
                className={`w-full px-4 py-2 rounded-lg transition-colors ${
                  action.primary 
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                }`}
              >
                {action.label}
              </button>
            ))}
          </div>

          {process.env.NODE_ENV === 'development' && this.state.error && (
            <details className="mt-4 text-left">
              <summary className="cursor-pointer text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
                Error Details (Development)
              </summary>
              <div className="mt-2 p-3 bg-gray-100 dark:bg-gray-700 rounded text-xs font-mono text-gray-700 dark:text-gray-300 overflow-auto">
                <div className="mb-2">
                  <strong>Error:</strong> {this.state.error.toString()}
                </div>
                <div className="mb-2">
                  <strong>Retry Count:</strong> {this.state.retryCount}
                </div>
                {this.state.errorInfo && (
                  <div>
                    <strong>Stack:</strong>
                    <pre className="whitespace-pre-wrap mt-1">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  </div>
                )}
              </div>
            </details>
          )}
        </div>
      </div>
    );
  }
}
