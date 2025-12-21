import React from 'react';
import { cn } from '../../lib/utils';

export interface ProgressCircleProps {
  progress: number; // 0-100
  size?: number;
  strokeWidth?: number;
  showPercentage?: boolean;
  showLabel?: boolean;
  label?: string;
  animated?: boolean;
  status?: 'pending' | 'processing' | 'completed' | 'failed';
  className?: string;
  children?: React.ReactNode;
}

export function ProgressCircle({
  progress,
  size = 120,
  strokeWidth = 8,
  showPercentage = true,
  showLabel = false,
  label,
  animated = true,
  status = 'pending',
  className,
  children
}: ProgressCircleProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDasharray = circumference;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  const getStatusColor = (status: string) => {
    const colors = {
      pending: 'text-gray-400',
      processing: 'text-blue-500',
      completed: 'text-green-500',
      failed: 'text-red-500'
    };
    return colors[status as keyof typeof colors] || colors.pending;
  };

  const getStatusBgColor = (status: string) => {
    const colors = {
      pending: 'bg-gray-100',
      processing: 'bg-blue-100',
      completed: 'bg-green-100',
      failed: 'bg-red-100'
    };
    return colors[status as keyof typeof colors] || colors.pending;
  };

  const getStatusStrokeColor = (status: string) => {
    const colors = {
      pending: 'stroke-gray-300',
      processing: 'stroke-blue-500',
      completed: 'stroke-green-500',
      failed: 'stroke-red-500'
    };
    return colors[status as keyof typeof colors] || colors.pending;
  };

  return (
    <div className={cn("flex flex-col items-center", className)}>
      <div className="relative" style={{ width: size, height: size }}>
        {/* Background Circle */}
        <svg
          width={size}
          height={size}
          className="transform -rotate-90"
        >
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            className={cn("text-gray-200", getStatusBgColor(status))}
            strokeWidth={strokeWidth}
          />
          
          {/* Progress Circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            className={cn(
              "transition-all duration-1000 ease-out",
              getStatusStrokeColor(status),
              animated && "animate-pulse"
            )}
            strokeWidth={strokeWidth}
            strokeDasharray={strokeDasharray}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
          />
        </svg>

        {/* Center Content */}
        <div className="absolute inset-0 flex items-center justify-center">
          {children || (
            <div className="text-center">
              {showPercentage && (
                <div className={cn(
                  "text-2xl font-bold",
                  getStatusColor(status)
                )}>
                  {Math.round(progress)}%
                </div>
              )}
              {showLabel && label && (
                <div className="text-sm text-gray-600 mt-1">
                  {label}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Status Text */}
      {status && (
        <div className="mt-3 text-center">
          <span className={cn(
            "text-sm font-medium px-3 py-1 rounded-full",
            getStatusBgColor(status),
            getStatusColor(status)
          )}>
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </span>
        </div>
      )}
    </div>
  );
}

// Enhanced Progress Circle with more features
export interface EnhancedProgressCircleProps extends ProgressCircleProps {
  showProgressText?: boolean;
  showStatusIcon?: boolean;
  onProgressComplete?: () => void;
  progressText?: string;
}

export function EnhancedProgressCircle({
  progress,
  showProgressText = true,
  showStatusIcon = true,
  onProgressComplete,
  progressText,
  ...props
}: EnhancedProgressCircleProps) {
  const isComplete = progress >= 100;
  const isProcessing = progress > 0 && progress < 100;

  React.useEffect(() => {
    if (isComplete && onProgressComplete) {
      onProgressComplete();
    }
  }, [isComplete, onProgressComplete]);

  const getStatusIcon = () => {
    if (isComplete) {
      return (
        <svg className="w-6 h-6 text-green-500" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
      );
    }
    
    if (isProcessing) {
      return (
        <svg className="w-6 h-6 text-blue-500 animate-spin" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
        </svg>
      );
    }

    return (
      <svg className="w-6 h-6 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
      </svg>
    );
  };

  return (
    <div className="space-y-4">
      <ProgressCircle
        progress={progress}
        {...props}
      >
        <div className="text-center">
          {showProgressText && (
            <div className="text-2xl font-bold text-gray-900">
              {progressText || `${Math.round(progress)}%`}
            </div>
          )}
          {showStatusIcon && (
            <div className="mt-2">
              {getStatusIcon()}
            </div>
          )}
        </div>
      </ProgressCircle>

      {/* Progress Details */}
      <div className="text-center space-y-2">
        <div className="text-sm text-gray-600">
          {isComplete && "Task completed successfully!"}
          {isProcessing && "Processing in progress..."}
          {!isProcessing && !isComplete && "Ready to start"}
        </div>
        
        {isProcessing && (
          <div className="text-xs text-gray-500">
            {progress < 25 && "Initializing..."}
            {progress >= 25 && progress < 50 && "Processing data..."}
            {progress >= 50 && progress < 75 && "Almost there..."}
            {progress >= 75 && progress < 100 && "Finalizing..."}
          </div>
        )}
      </div>
    </div>
  );
}

// Multi-Size Progress Circle
export interface MultiSizeProgressCircleProps extends ProgressCircleProps {
  sizes?: ('sm' | 'md' | 'lg' | 'xl')[];
  variant?: 'default' | 'compact' | 'detailed';
}

export function MultiSizeProgressCircle({
  sizes = ['md'],
  variant = 'default',
  ...props
}: MultiSizeProgressCircleProps) {
  const sizeMap = {
    sm: 80,
    md: 120,
    lg: 160,
    xl: 200
  };

  const variantConfig = {
    default: { showPercentage: true, showLabel: false },
    compact: { showPercentage: false, showLabel: false },
    detailed: { showPercentage: true, showLabel: true }
  };

  const config = variantConfig[variant];

  return (
    <div className="flex flex-wrap gap-4 justify-center">
      {sizes.map((size) => (
        <ProgressCircle
          key={size}
          size={sizeMap[size]}
          {...config}
          {...props}
        />
      ))}
    </div>
  );
}
