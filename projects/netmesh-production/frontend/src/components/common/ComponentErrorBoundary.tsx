/**
 * ComponentErrorBoundary - Component-level error boundary with inline fallbacks
 * Used for individual components to prevent cascading failures
 */

import React from 'react';
import { ErrorBoundary } from './ErrorBoundary';

interface ComponentErrorBoundaryProps {
  children: React.ReactNode;
  componentName: string;
  fallback?: React.ReactNode;
  showRetry?: boolean;
  isolate?: boolean;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

export const ComponentErrorBoundary: React.FC<ComponentErrorBoundaryProps> = ({
  children,
  componentName,
  fallback,
  showRetry = true,
  isolate = false,
  onError
}) => {
  const defaultFallback = isolate ? (
    <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 text-center">
      <div className="w-8 h-8 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-2">
        <svg className="w-4 h-4 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
        {componentName} unavailable
      </p>
    </div>
  ) : (
    <div className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-lg p-3">
      <div className="flex items-center">
        <div className="flex-shrink-0">
          <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div className="ml-2">
          <p className="text-sm text-red-700 dark:text-red-400">
            {componentName} component error
          </p>
        </div>
      </div>
    </div>
  );

  return (
    <ErrorBoundary
      level="component"
      fallback={fallback || defaultFallback}
      showReload={false}
      showRetry={showRetry}
      onError={onError}
      isolate={isolate}
      context={{ componentName }}
    >
      {children}
    </ErrorBoundary>
  );
};