import React, { Component, ErrorInfo, ReactNode } from 'react';
import { getLogger } from '@repo/logger';

const logger = getLogger({ name: 'error-boundary' });

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorId?: string;
  recoveryAttempts: number;
}

export class ErrorBoundary extends Component<Props, State> {
  private readonly MAX_RECOVERY_ATTEMPTS = 3;

  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      recoveryAttempts: 0,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
      errorId: `ERR_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    logger.error(error, {
      errorId: this.state.errorId,
      componentStack: errorInfo.componentStack,
      recoveryAttempts: this.state.recoveryAttempts,
    });

    this.props.onError?.(error, errorInfo);

    // Auto-recover from recoverable errors
    if (this.isRecoverableError(error) && this.state.recoveryAttempts < this.MAX_RECOVERY_ATTEMPTS) {
      this.attemptRecovery();
    }
  }

  private isRecoverableError(error: Error): boolean {
    const recoverablePatterns = [
      /ChunkLoadError/,
      /Loading chunk.*failed/,
      /Network.*Error/,
      /ResizeObserver loop/,
    ];

    return recoverablePatterns.some((pattern) =>
      pattern.test(error.message) || pattern.test(error.name)
    );
  }

  private attemptRecovery = () => {
    const recoveryDelay = Math.pow(2, this.state.recoveryAttempts) * 2000;

    setTimeout(() => {
      this.setState({
        hasError: false,
        error: undefined,
        recoveryAttempts: this.state.recoveryAttempts + 1,
      });

      logger.info('Automatic recovery attempted', {
        attempt: this.state.recoveryAttempts + 1,
        delay: recoveryDelay,
      });
    }, recoveryDelay);
  };

  private handleRetry = () => {
    this.setState({
      hasError: false,
      error: undefined,
      recoveryAttempts: this.state.recoveryAttempts + 1,
    });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
          <div className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full">
            <div className="text-center">
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>

              <h2 className="text-xl font-semibold text-gray-900 mb-2">Something went wrong</h2>
              <p className="text-gray-600 mb-6">We encountered an error. Please try again.</p>

              {this.state.errorId && (
                <div className="bg-gray-50 rounded p-3 mb-6">
                  <div className="text-xs text-gray-500 mb-1">Error Reference</div>
                  <div className="font-mono text-sm text-gray-700">{this.state.errorId}</div>
                </div>
              )}

              <div className="space-y-2">
                {this.state.recoveryAttempts < this.MAX_RECOVERY_ATTEMPTS && (
                  <button
                    onClick={this.handleRetry}
                    className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Try Again
                  </button>
                )}

                <button
                  onClick={() => window.location.reload()}
                  className="w-full bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300 transition-colors"
                >
                  Reload Page
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
