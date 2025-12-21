/**
 * FeatureErrorBoundary - Feature-level error boundary with lightweight fallbacks
 * Used to isolate errors within specific features without affecting the entire app
 */

import React from 'react';
import { ErrorBoundary, ErrorAction } from './ErrorBoundary';

interface FeatureErrorBoundaryProps {
  children: React.ReactNode;
  featureName: string;
  fallback?: React.ReactNode;
  showRetry?: boolean;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

export const FeatureErrorBoundary: React.FC<FeatureErrorBoundaryProps> = ({
  children,
  featureName,
  fallback,
  showRetry = true,
  onError
}) => {
  const defaultFallback = (
    <div className="bg-yellow-50 dark:bg-yellow-900/10 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 my-4">
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg className="w-5 h-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <div className="ml-3">
          <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-300">
            {featureName} Temporarily Unavailable
          </h3>
          <p className="mt-1 text-sm text-yellow-700 dark:text-yellow-400">
            This feature is experiencing issues. Our team has been notified.
          </p>
        </div>
      </div>
    </div>
  );

  return (
    <ErrorBoundary
      level="feature"
      fallback={fallback || defaultFallback}
      showReload={false}
      showRetry={showRetry}
      onError={onError}
      context={{ featureName }}
    >
      {children}
    </ErrorBoundary>
  );
};