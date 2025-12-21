import React from 'react';
import { cn } from '../../lib/utils';

export interface ProgressSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'default' | 'dots' | 'bars' | 'pulse' | 'ripple';
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info';
  text?: string;
  showText?: boolean;
  animated?: boolean;
  className?: string;
}

export function ProgressSpinner({
  size = 'md',
  variant = 'default',
  color = 'primary',
  text,
  showText = false,
  animated = true,
  className
}: ProgressSpinnerProps) {
  const sizeMap = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16'
  };

  const colorMap = {
    primary: 'text-blue-500',
    secondary: 'text-gray-500',
    success: 'text-green-500',
    warning: 'text-yellow-500',
    error: 'text-red-500',
    info: 'text-blue-400'
  };

  const renderSpinner = () => {
    switch (variant) {
      case 'dots':
        return (
          <div className={cn("flex space-x-1", sizeMap[size])}>
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className={cn(
                  "rounded-full bg-current",
                  size === 'sm' && "w-1 h-1",
                  size === 'md' && "w-2 h-2",
                  size === 'lg' && "w-3 h-3",
                  size === 'xl' && "w-4 h-4"
                )}
                style={{
                  animation: animated ? `bounce 1.4s ease-in-out infinite both` : 'none',
                  animationDelay: `${i * 0.16}s`
                }}
              />
            ))}
          </div>
        );

      case 'bars':
        return (
          <div className={cn("flex space-x-1", sizeMap[size])}>
            {[0, 1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className={cn(
                  "bg-current rounded-sm",
                  size === 'sm' && "w-1 h-4",
                  size === 'md' && "w-1.5 h-6",
                  size === 'lg' && "w-2 h-8",
                  size === 'xl' && "w-3 h-12"
                )}
                style={{
                  animation: animated ? `bars 1.2s ease-in-out infinite both` : 'none',
                  animationDelay: `${i * 0.1}s`
                }}
              />
            ))}
          </div>
        );

      case 'pulse':
        return (
          <div
            className={cn(
              "rounded-full bg-current",
              sizeMap[size]
            )}
            style={{
              animation: animated ? 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' : 'none'
            }}
          />
        );

      case 'ripple':
        return (
          <div className={cn("relative", sizeMap[size])}>
            <div
              className={cn(
                "absolute inset-0 rounded-full border-2 border-current opacity-75",
                sizeMap[size]
              )}
              style={{
                animation: animated ? 'ripple 1s linear infinite' : 'none'
              }}
            />
            <div
              className={cn(
                "absolute inset-0 rounded-full border-2 border-current opacity-75",
                sizeMap[size]
              )}
              style={{
                animation: animated ? 'ripple 1s linear infinite 0.5s' : 'none'
              }}
            />
          </div>
        );

      default:
        return (
          <svg
            className={cn(
              "animate-spin",
              sizeMap[size],
              !animated && "animate-none"
            )}
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        );
    }
  };

  return (
    <div className={cn("flex flex-col items-center", className)}>
      <div className={cn(colorMap[color])}>
        {renderSpinner()}
      </div>
      
      {showText && text && (
        <div className="mt-3 text-center">
          <p className={cn(
            "text-sm font-medium",
            size === 'sm' && "text-xs",
            size === 'md' && "text-sm",
            size === 'lg' && "text-base",
            size === 'xl' && "text-lg"
          )}>
            {text}
          </p>
        </div>
      )}
    </div>
  );
}

// Enhanced Progress Spinner with more features
export interface EnhancedProgressSpinnerProps extends ProgressSpinnerProps {
  showProgress?: boolean;
  progress?: number;
  showETA?: boolean;
  estimatedTime?: number;
  onComplete?: () => void;
}

export function EnhancedProgressSpinner({
  showProgress = false,
  progress = 0,
  showETA = false,
  estimatedTime = 0,
  onComplete,
  ...props
}: EnhancedProgressSpinnerProps) {
  React.useEffect(() => {
    if (progress >= 100 && onComplete) {
      onComplete();
    }
  }, [progress, onComplete]);

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  };

  return (
    <div className="space-y-4">
      <ProgressSpinner {...props} />
      
      {/* Progress Information */}
      {showProgress && (
        <div className="text-center space-y-2">
          <div className="text-sm font-medium text-gray-700">
            {Math.round(progress)}% Complete
          </div>
          
          {/* Progress Bar */}
          <div className="w-32 bg-gray-200 rounded-full h-2 mx-auto">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          
          {/* ETA */}
          {showETA && estimatedTime > 0 && (
            <div className="text-xs text-gray-500">
              Estimated time remaining: {formatTime(estimatedTime)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Multi-Spinner Component
export interface MultiSpinnerProps {
  spinners: Array<{
    id: string;
    variant: ProgressSpinnerProps['variant'];
    size: ProgressSpinnerProps['size'];
    color: ProgressSpinnerProps['color'];
    text?: string;
  }>;
  layout?: 'horizontal' | 'vertical' | 'grid';
  className?: string;
}

export function MultiSpinner({
  spinners,
  layout = 'horizontal',
  className
}: MultiSpinnerProps) {
  const layoutClasses = {
    horizontal: 'flex space-x-4',
    vertical: 'flex flex-col space-y-4',
    grid: 'grid grid-cols-2 gap-4'
  };

  return (
    <div className={cn(layoutClasses[layout], className)}>
      {spinners.map((spinner) => (
        <ProgressSpinner
          key={spinner.id}
          variant={spinner.variant}
          size={spinner.size}
          color={spinner.color}
          text={spinner.text}
          showText={!!spinner.text}
        />
      ))}
    </div>
  );
}

// Loading Overlay Component
export interface LoadingOverlayProps {
  isLoading: boolean;
  text?: string;
  spinnerProps?: ProgressSpinnerProps;
  overlayClassName?: string;
  children?: React.ReactNode;
}

export function LoadingOverlay({
  isLoading,
  text = 'Loading...',
  spinnerProps,
  overlayClassName,
  children
}: LoadingOverlayProps) {
  if (!isLoading) {
    return <>{children}</>;
  }

  return (
    <div className="relative">
      {children}
      <div
        className={cn(
          "absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center z-50",
          overlayClassName
        )}
      >
        <div className="text-center">
          <ProgressSpinner
            size="lg"
            variant="default"
            color="primary"
            text={text}
            showText={true}
            {...spinnerProps}
          />
        </div>
      </div>
    </div>
  );
}

// Add CSS animations to the global styles
const spinnerStyles = `
  @keyframes bounce {
    0%, 80%, 100% {
      transform: scale(0);
    }
    40% {
      transform: scale(1);
    }
  }

  @keyframes bars {
    0%, 40%, 100% {
      transform: scaleY(0.4);
    }
    20% {
      transform: scaleY(1);
    }
  }

  @keyframes ripple {
    0% {
      transform: scale(0);
      opacity: 1;
    }
    100% {
      transform: scale(4);
      opacity: 0;
    }
  }
`;

// Inject styles if not already present
if (typeof document !== 'undefined') {
  const styleId = 'progress-spinner-styles';
  if (!document.getElementById(styleId)) {
    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = spinnerStyles;
    document.head.appendChild(style);
  }
}
