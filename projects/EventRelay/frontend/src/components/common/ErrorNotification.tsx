/**
 * ErrorNotification - User-friendly error notifications with contextual help
 * Provides non-intrusive error feedback with actionable suggestions
 */

import React, { useState, useEffect } from 'react';
import { ErrorLogger } from '../../services/ErrorLogger';

export type NotificationSeverity = 'info' | 'warning' | 'error' | 'success';

export interface ErrorNotificationProps {
  title: string;
  message: string;
  severity: NotificationSeverity;
  persistent?: boolean;
  autoHideDuration?: number;
  showDetails?: boolean;
  troubleshootingSteps?: string[];
  actions?: Array<{
    label: string;
    onClick: () => void;
    primary?: boolean;
  }>;
  onClose?: () => void;
  onFeedback?: (helpful: boolean, feedback?: string) => void;
}

export const ErrorNotification: React.FC<ErrorNotificationProps> = ({
  title,
  message,
  severity,
  persistent = false,
  autoHideDuration = 5000,
  showDetails = false,
  troubleshootingSteps = [],
  actions = [],
  onClose,
  onFeedback
}) => {
  const [isVisible, setIsVisible] = useState(true);
  const [showTroubleshooting, setShowTroubleshooting] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState(false);
  const [feedbackText, setFeedbackText] = useState('');
  
  const errorLogger = new ErrorLogger();

  useEffect(() => {
    if (!persistent && autoHideDuration > 0) {
      const timer = setTimeout(() => {
        setIsVisible(false);
        onClose?.();
      }, autoHideDuration);
      
      return () => clearTimeout(timer);
    }
  }, [persistent, autoHideDuration, onClose]);

  const handleClose = () => {
    setIsVisible(false);
    onClose?.();
  };

  const handleFeedback = (helpful: boolean) => {
    setFeedbackGiven(true);
    onFeedback?.(helpful, feedbackText);
    
    errorLogger.info('User provided error feedback', {
      helpful,
      feedback: feedbackText,
      errorTitle: title,
      severity
    });
  };

  const getSeverityStyles = () => {
    switch (severity) {
      case 'error':
        return {
          container: 'bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-800',
          icon: 'text-red-400',
          title: 'text-red-800 dark:text-red-300',
          message: 'text-red-700 dark:text-red-400',
          button: 'text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/20'
        };
      case 'warning':
        return {
          container: 'bg-yellow-50 dark:bg-yellow-900/10 border-yellow-200 dark:border-yellow-800',
          icon: 'text-yellow-400',
          title: 'text-yellow-800 dark:text-yellow-300',
          message: 'text-yellow-700 dark:text-yellow-400',
          button: 'text-yellow-600 dark:text-yellow-400 hover:bg-yellow-100 dark:hover:bg-yellow-900/20'
        };
      case 'info':
        return {
          container: 'bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-800',
          icon: 'text-blue-400',
          title: 'text-blue-800 dark:text-blue-300',
          message: 'text-blue-700 dark:text-blue-400',
          button: 'text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/20'
        };
      case 'success':
        return {
          container: 'bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-800',
          icon: 'text-green-400',
          title: 'text-green-800 dark:text-green-300',
          message: 'text-green-700 dark:text-green-400',
          button: 'text-green-600 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/20'
        };
      default:
        return {
          container: 'bg-gray-50 dark:bg-gray-900/10 border-gray-200 dark:border-gray-800',
          icon: 'text-gray-400',
          title: 'text-gray-800 dark:text-gray-300',
          message: 'text-gray-700 dark:text-gray-400',
          button: 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-900/20'
        };
    }
  };

  const getSeverityIcon = () => {
    switch (severity) {
      case 'error':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'warning':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        );
      case 'info':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'success':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      default:
        return null;
    }
  };

  const styles = getSeverityStyles();

  if (!isVisible) return null;

  return (
    <div className={`border rounded-lg p-4 shadow-sm ${styles.container} transition-all duration-300`}>
      <div className="flex items-start">
        <div className={`flex-shrink-0 ${styles.icon}`}>
          {getSeverityIcon()}
        </div>
        <div className="ml-3 flex-grow">
          <h3 className={`text-sm font-medium ${styles.title}`}>
            {title}
          </h3>
          <div className={`mt-2 text-sm ${styles.message}`}>
            <p>{message}</p>
          </div>

          {/* Action buttons */}
          {actions.length > 0 && (
            <div className="mt-3 flex space-x-2">
              {actions.map((action, index) => (
                <button
                  key={index}
                  onClick={action.onClick}
                  className={`inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                    action.primary
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : `${styles.button} border border-current`
                  }`}
                >
                  {action.label}
                </button>
              ))}
            </div>
          )}

          {/* Troubleshooting steps */}
          {troubleshootingSteps.length > 0 && (
            <div className="mt-3">
              <button
                onClick={() => setShowTroubleshooting(!showTroubleshooting)}
                className={`text-xs ${styles.button} underline hover:no-underline`}
              >
                {showTroubleshooting ? 'Hide' : 'Show'} troubleshooting steps
              </button>
              
              {showTroubleshooting && (
                <div className="mt-2 pl-4 border-l-2 border-current opacity-75">
                  <ol className="text-xs space-y-1 list-decimal list-inside">
                    {troubleshootingSteps.map((step, index) => (
                      <li key={index}>{step}</li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          )}

          {/* Feedback section */}
          {onFeedback && !feedbackGiven && severity === 'error' && (
            <div className="mt-3 pt-3 border-t border-current opacity-20">
              <p className={`text-xs ${styles.message} mb-2`}>
                Was this error message helpful?
              </p>
              <div className="flex items-center space-x-3">
                <button
                  onClick={() => handleFeedback(true)}
                  className={`text-xs ${styles.button} hover:underline`}
                >
                  Yes, it helped
                </button>
                <button
                  onClick={() => handleFeedback(false)}
                  className={`text-xs ${styles.button} hover:underline`}
                >
                  No, could be better
                </button>
              </div>
              <textarea
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
                placeholder="Optional: Tell us how we can improve..."
                className="mt-2 w-full text-xs p-2 border border-gray-300 dark:border-gray-600 rounded bg-transparent resize-none"
                rows={2}
              />
            </div>
          )}

          {feedbackGiven && (
            <div className="mt-3 pt-3 border-t border-current opacity-20">
              <p className={`text-xs ${styles.message}`}>
                Thank you for your feedback! We'll use it to improve our error messages.
              </p>
            </div>
          )}
        </div>
        
        {/* Close button */}
        <div className="ml-4 flex-shrink-0">
          <button
            onClick={handleClose}
            className={`inline-flex rounded-md p-1.5 ${styles.button} transition-colors`}
          >
            <span className="sr-only">Dismiss</span>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};