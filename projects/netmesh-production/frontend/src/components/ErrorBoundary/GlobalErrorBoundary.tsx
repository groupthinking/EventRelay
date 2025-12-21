import React, { Component, ErrorInfo, ReactNode } from 'react';
import { ErrorReporter } from '../../services/ErrorReporter';
import { ErrorLogger } from '../../services/ErrorLogger';
import { ErrorNotification } from '../common/ErrorNotification';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  enableRecovery?: boolean;
  enableReporting?: boolean;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
  errorId?: string;
  recoveryAttempts: number;
  isRecovering: boolean;
  showDetails: boolean;
}

/**
 * GlobalErrorBoundary - Enterprise-grade error boundary for application-wide error handling
 * 
 * Features:
 * - Automatic error recovery with exponential backoff
 * - Structured error reporting and analytics
 * - User-friendly error display with contextual help
 * - Development-friendly error details
 * - Comprehensive error logging and monitoring
 */
export class GlobalErrorBoundary extends Component<Props, State> {
  private errorReporter: ErrorReporter;
  private errorLogger: ErrorLogger;
  private recoveryTimer?: NodeJS.Timeout;
  private readonly MAX_RECOVERY_ATTEMPTS = 3;

  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      recoveryAttempts: 0,
      isRecovering: false,
      showDetails: false
    };
    
    this.errorReporter = new ErrorReporter();
    this.errorLogger = new ErrorLogger();
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
      errorId: `GLOBAL_ERR_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    };
  }

  async componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const { enableReporting = true } = this.props;
    
    // Create comprehensive error context
    const errorContext = {
      level: 'global',
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
        url: window.location.href,
        userAgent: navigator.userAgent,
        timestamp: new Date().toISOString(),
        userId: this.getUserId(),
        sessionId: this.getSessionId(),
        viewport: {
          width: window.innerWidth,
          height: window.innerHeight
        },
        localStorage: this.getLocalStorageSnapshot(),
        memoryInfo: this.getMemoryInfo(),
        connectionInfo: this.getConnectionInfo(),
        recoveryAttempts: this.state.recoveryAttempts
      },
      severity: 'critical' as const,
      retryCount: this.state.recoveryAttempts,
      tags: ['global-error', 'critical', 'application-failure']
    };

    // Log error with full context
    this.errorLogger.fatal('Global application error', error, errorContext);
    
    // Report to monitoring service
    if (enableReporting) {
      try {
        await this.errorReporter.reportError(errorContext);
      } catch (reportingError) {
        console.warn('Failed to report global error:', reportingError);
        this.errorLogger.error('Error reporting failed', reportingError);
      }
    }

    this.setState({ error, errorInfo });
    
    // Attempt automatic recovery for recoverable errors
    if (this.isRecoverableError(error) && this.state.recoveryAttempts < this.MAX_RECOVERY_ATTEMPTS) {
      this.attemptRecovery();
    }
  }

  private getUserId(): string {
    return localStorage.getItem('userId') || sessionStorage.getItem('userId') || 'anonymous';
  }

  private getSessionId(): string {
    let sessionId = sessionStorage.getItem('sessionId');
    if (!sessionId) {
      sessionId = `global_session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('sessionId', sessionId);
    }
    return sessionId;
  }

  private getLocalStorageSnapshot(): Record<string, any> {
    try {
      const snapshot: Record<string, any> = {};
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && !key.includes('sensitive') && !key.includes('password')) {
          snapshot[key] = localStorage.getItem(key);
        }
      }
      return snapshot;
    } catch (error) {
      return { error: 'Unable to capture localStorage snapshot' };
    }
  }

  private getMemoryInfo(): any {
    try {
      return (performance as any).memory ? {
        usedJSHeapSize: (performance as any).memory.usedJSHeapSize,
        totalJSHeapSize: (performance as any).memory.totalJSHeapSize,
        jsHeapSizeLimit: (performance as any).memory.jsHeapSizeLimit
      } : null;
    } catch (error) {
      return null;
    }
  }

  private getConnectionInfo(): any {
    try {
      return (navigator as any).connection ? {
        effectiveType: (navigator as any).connection.effectiveType,
        downlink: (navigator as any).connection.downlink,
        rtt: (navigator as any).connection.rtt
      } : null;
    } catch (error) {
      return null;
    }
  }

  private isRecoverableError(error: Error): boolean {
    const recoverablePatterns = [
      /ChunkLoadError/,
      /Loading chunk \d+ failed/,
      /Network.*Error/,
      /fetch.*failed/,
      /Script error/,
      /ResizeObserver loop limit exceeded/
    ];
    
    return recoverablePatterns.some(pattern => 
      pattern.test(error.message) || pattern.test(error.name)
    );
  }

  private attemptRecovery = () => {
    this.setState({ isRecovering: true });
    
    // Clear any cached resources that might be causing issues
    this.clearApplicationCache();
    
    const recoveryDelay = Math.pow(2, this.state.recoveryAttempts) * 2000; // 2s, 4s, 8s
    
    this.recoveryTimer = setTimeout(() => {
      this.setState({
        hasError: false,
        error: undefined,
        errorInfo: undefined,
        recoveryAttempts: this.state.recoveryAttempts + 1,
        isRecovering: false
      });
      
      this.errorLogger.info('Automatic recovery attempted', {
        attempt: this.state.recoveryAttempts + 1,
        delay: recoveryDelay
      });
    }, recoveryDelay);
  };

  private clearApplicationCache = () => {
    try {
      // Clear service worker cache if available
      if ('serviceWorker' in navigator) {
        navigator.serviceWorker.ready.then(registration => {
          if (registration.active) {
            registration.active.postMessage({ type: 'CLEAR_CACHE' });
          }
        });
      }
      
      // Clear session storage (except session ID)
      const sessionId = sessionStorage.getItem('sessionId');
      sessionStorage.clear();
      if (sessionId) {
        sessionStorage.setItem('sessionId', sessionId);
      }
    } catch (error) {
      console.warn('Failed to clear application cache:', error);
    }
  };

  private handleRetry = () => {
    this.setState({
      hasError: false,
      error: undefined,
      errorInfo: undefined,
      recoveryAttempts: this.state.recoveryAttempts + 1
    });
  };

  private handleReload = () => {
    // Clear all caches before reload
    this.clearApplicationCache();
    
    // Add reload indicator to prevent infinite loops
    sessionStorage.setItem('reloaded_after_error', 'true');
    
    setTimeout(() => {
      window.location.reload();
    }, 100);
  };

  private handleReportProblem = () => {
    const mailtoLink = `mailto:support@uvai.com?subject=Application Error Report&body=Error ID: ${this.state.errorId}%0A%0APlease describe what you were doing when this error occurred:%0A%0A`;
    window.open(mailtoLink);
  };

  private toggleDetails = () => {
    this.setState({ showDetails: !this.state.showDetails });
  };

  componentWillUnmount() {
    if (this.recoveryTimer) {
      clearTimeout(this.recoveryTimer);
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

      return this.renderGlobalError();
    }

    return this.props.children;
  }

  private renderRecovering() {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-8 max-w-md w-full text-center">
          <div className="relative w-16 h-16 mx-auto mb-6">
            <div className="absolute inset-0 bg-blue-600 rounded-full animate-ping"></div>
            <div className="relative w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-white animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </div>
          </div>
          
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Recovering Application
          </h2>
          
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            We detected an issue and are automatically fixing it. This should only take a moment.
          </p>
          
          <div className="text-sm text-gray-500 dark:text-gray-500">
            Recovery attempt {this.state.recoveryAttempts + 1} of {this.MAX_RECOVERY_ATTEMPTS}
          </div>
        </div>
      </div>
    );
  }

  private renderGlobalError() {
    const canRetry = this.state.recoveryAttempts < this.MAX_RECOVERY_ATTEMPTS;
    
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-pink-100 dark:from-gray-900 dark:to-red-900/20 flex items-center justify-center p-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-8 max-w-lg w-full">
          {/* Error Icon */}
          <div className="w-20 h-20 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-10 h-10 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>

          {/* Error Message */}
          <div className="text-center mb-6">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Application Error
            </h1>
            
            <p className="text-gray-600 dark:text-gray-400 mb-2">
              Something unexpected happened. We've been automatically notified and are working to fix this issue.
            </p>
            
            <p className="text-sm text-gray-500 dark:text-gray-500">
              If this problem persists, please contact our support team.
            </p>
          </div>

          {/* Error ID */}
          {this.state.errorId && (
            <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 mb-6">
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Error Reference</div>
              <div className="font-mono text-sm text-gray-700 dark:text-gray-300">
                {this.state.errorId}
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="space-y-3 mb-6">
            {canRetry && (
              <button
                onClick={this.handleRetry}
                className="w-full bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                Try Again
              </button>
            )}
            
            <button
              onClick={this.handleReload}
              className="w-full bg-gray-600 dark:bg-gray-700 text-white px-6 py-3 rounded-lg hover:bg-gray-700 dark:hover:bg-gray-600 transition-colors font-medium"
            >
              Reload Application
            </button>
            
            <button
              onClick={this.handleReportProblem}
              className="w-full bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300 px-6 py-3 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-500 transition-colors font-medium"
            >
              Report Problem
            </button>
          </div>

          {/* Development Details */}
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
              <button
                onClick={this.toggleDetails}
                className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 flex items-center"
              >
                <svg className={`w-4 h-4 mr-1 transform ${this.state.showDetails ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                Developer Details
              </button>
              
              {this.state.showDetails && (
                <div className="mt-3 p-3 bg-gray-100 dark:bg-gray-700 rounded text-xs font-mono text-gray-700 dark:text-gray-300 overflow-auto max-h-40">
                  <div className="mb-2">
                    <strong>Error:</strong> {this.state.error.toString()}
                  </div>
                  <div className="mb-2">
                    <strong>Recovery Attempts:</strong> {this.state.recoveryAttempts}
                  </div>
                  {this.state.errorInfo && (
                    <div>
                      <strong>Component Stack:</strong>
                      <pre className="whitespace-pre-wrap mt-1 text-xs">
                        {this.state.errorInfo.componentStack}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }
}