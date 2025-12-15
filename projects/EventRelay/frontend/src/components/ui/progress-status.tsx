import React from 'react';
import { cn } from '../../lib/utils';

export type StatusType = 'pending' | 'active' | 'processing' | 'completed' | 'failed' | 'warning' | 'info' | 'success';

export interface ProgressStatusProps {
  status: StatusType;
  text?: string;
  showIcon?: boolean;
  showBadge?: boolean;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'outline' | 'solid' | 'minimal';
  className?: string;
  children?: React.ReactNode;
}

export function ProgressStatus({
  status,
  text,
  showIcon = true,
  showBadge = true,
  size = 'md',
  variant = 'default',
  className,
  children
}: ProgressStatusProps) {
  const getStatusConfig = (status: StatusType) => {
    const configs = {
      pending: {
        icon: (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
          </svg>
        ),
        colors: {
          default: 'text-gray-600 bg-gray-100 border-gray-200',
          outline: 'text-gray-600 border-gray-300',
          solid: 'text-white bg-gray-500 border-gray-500',
          minimal: 'text-gray-600'
        }
      },
      active: {
        icon: (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
          </svg>
        ),
        colors: {
          default: 'text-blue-600 bg-blue-100 border-blue-200',
          outline: 'text-blue-600 border-blue-300',
          solid: 'text-white bg-blue-500 border-blue-500',
          minimal: 'text-blue-600'
        }
      },
      processing: {
        icon: (
          <svg className="w-4 h-4 animate-spin" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
          </svg>
        ),
        colors: {
          default: 'text-yellow-600 bg-yellow-100 border-yellow-200',
          outline: 'text-yellow-600 border-yellow-300',
          solid: 'text-white bg-yellow-500 border-yellow-500',
          minimal: 'text-yellow-600'
        }
      },
      completed: {
        icon: (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        ),
        colors: {
          default: 'text-green-600 bg-green-100 border-green-200',
          outline: 'text-green-600 border-green-300',
          solid: 'text-white bg-green-500 border-green-500',
          minimal: 'text-green-600'
        }
      },
      failed: {
        icon: (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        ),
        colors: {
          default: 'text-red-600 bg-red-100 border-red-200',
          outline: 'text-red-600 border-red-300',
          solid: 'text-white bg-red-500 border-red-500',
          minimal: 'text-red-600'
        }
      },
      warning: {
        icon: (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        ),
        colors: {
          default: 'text-yellow-600 bg-yellow-100 border-yellow-200',
          outline: 'text-yellow-600 border-yellow-300',
          solid: 'text-white bg-yellow-500 border-yellow-500',
          minimal: 'text-yellow-600'
        }
      },
      info: {
        icon: (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
        ),
        colors: {
          default: 'text-blue-600 bg-blue-100 border-blue-200',
          outline: 'text-blue-600 border-blue-300',
          solid: 'text-white bg-blue-500 border-blue-500',
          minimal: 'text-blue-600'
        }
      },
      success: {
        icon: (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        ),
        colors: {
          default: 'text-green-600 bg-green-100 border-green-200',
          outline: 'text-green-600 border-green-300',
          solid: 'text-white bg-green-500 border-green-500',
          minimal: 'text-green-600'
        }
      }
    };

    return configs[status] || configs.pending;
  };

  const getSizeClasses = (size: string) => {
    const sizes = {
      sm: {
        container: 'px-2 py-1 text-xs',
        icon: 'w-3 h-3',
        text: 'text-xs'
      },
      md: {
        container: 'px-3 py-1.5 text-sm',
        icon: 'w-4 h-4',
        text: 'text-sm'
      },
      lg: {
        container: 'px-4 py-2 text-base',
        icon: 'w-5 h-5',
        text: 'text-base'
      }
    };

    return sizes[size as keyof typeof sizes] || sizes.md;
  };

  const statusConfig = getStatusConfig(status);
  const sizeClasses = getSizeClasses(size);

  const renderStatus = () => {
    if (variant === 'minimal') {
      return (
        <div className={cn("flex items-center gap-2", className)}>
          {showIcon && (
            <div className={cn(sizeClasses.icon, statusConfig.colors.minimal)}>
              {statusConfig.icon}
            </div>
          )}
          {text && (
            <span className={cn(sizeClasses.text, "font-medium", statusConfig.colors.minimal)}>
              {text}
            </span>
          )}
          {children}
        </div>
      );
    }

    const baseClasses = cn(
      "inline-flex items-center gap-2 font-medium rounded-md border transition-colors duration-200",
      sizeClasses.container,
      statusConfig.colors[variant],
      className
    );

    return (
      <div className={baseClasses}>
        {showIcon && (
          <div className={sizeClasses.icon}>
            {statusConfig.icon}
          </div>
        )}
        {text && (
          <span className={sizeClasses.text}>
            {text}
          </span>
        )}
        {children}
      </div>
    );
  };

  if (!showBadge) {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        {showIcon && (
          <div className={cn(sizeClasses.icon, statusConfig.colors.minimal)}>
            {statusConfig.icon}
          </div>
        )}
        {text && (
          <span className={cn(sizeClasses.text, "font-medium", statusConfig.colors.minimal)}>
            {text}
          </span>
        )}
        {children}
      </div>
    );
  }

  return renderStatus();
}

// Enhanced Progress Status with more features
export interface EnhancedProgressStatusProps extends ProgressStatusProps {
  showProgress?: boolean;
  progress?: number;
  showETA?: boolean;
  estimatedTime?: number;
  showDetails?: boolean;
  details?: React.ReactNode;
  onStatusChange?: (status: StatusType) => void;
}

export function EnhancedProgressStatus({
  showProgress = false,
  progress = 0,
  showETA = false,
  estimatedTime = 0,
  showDetails = false,
  details,
  onStatusChange,
  ...props
}: EnhancedProgressStatusProps) {
  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  };

  return (
    <div className="space-y-3">
      <ProgressStatus {...props} />
      
      {/* Progress Information */}
      {showProgress && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Progress</span>
            <span className="font-medium text-gray-900">{Math.round(progress)}%</span>
          </div>
          
          {/* Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          
          {/* ETA */}
          {showETA && estimatedTime > 0 && (
            <div className="text-xs text-gray-500 text-center">
              Estimated time remaining: {formatTime(estimatedTime)}
            </div>
          )}
        </div>
      )}

      {/* Additional Details */}
      {showDetails && details && (
        <div className="p-3 bg-gray-50 rounded-lg">
          {details}
        </div>
      )}
    </div>
  );
}

// Status Group Component
export interface StatusGroupProps {
  statuses: Array<{
    id: string;
    status: StatusType;
    text: string;
    showIcon?: boolean;
    size?: ProgressStatusProps['size'];
    variant?: ProgressStatusProps['variant'];
  }>;
  layout?: 'horizontal' | 'vertical' | 'grid';
  className?: string;
}

export function StatusGroup({
  statuses,
  layout = 'horizontal',
  className
}: StatusGroupProps) {
  const layoutClasses = {
    horizontal: 'flex flex-wrap gap-2',
    vertical: 'flex flex-col gap-2',
    grid: 'grid grid-cols-2 gap-2'
  };

  return (
    <div className={cn(layoutClasses[layout], className)}>
      {statuses.map((statusItem) => (
        <ProgressStatus
          key={statusItem.id}
          status={statusItem.status}
          text={statusItem.text}
          showIcon={statusItem.showIcon}
          size={statusItem.size}
          variant={statusItem.variant}
        />
      ))}
    </div>
  );
}

// Status Timeline Component
export interface StatusTimelineProps {
  statuses: Array<{
    id: string;
    status: StatusType;
    text: string;
    timestamp: Date;
    description?: string;
  }>;
  className?: string;
}

export function StatusTimeline({
  statuses,
  className
}: StatusTimelineProps) {
  const sortedStatuses = [...statuses].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());

  const formatTimestamp = (timestamp: Date) => {
    const now = new Date();
    const diff = now.getTime() - timestamp.getTime();
    const minutes = Math.floor(diff / (1000 * 60));
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    
    return timestamp.toLocaleDateString();
  };

  return (
    <div className={cn("space-y-4", className)}>
      {sortedStatuses.map((statusItem, index) => (
        <div key={statusItem.id} className="flex items-start gap-3">
          {/* Status Icon */}
          <div className="mt-1">
            <ProgressStatus
              status={statusItem.status}
              size="sm"
              variant="minimal"
              showBadge={false}
            />
          </div>

          {/* Status Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-900">
                {statusItem.text}
              </span>
              <span className="text-xs text-gray-500">
                {formatTimestamp(statusItem.timestamp)}
              </span>
            </div>
            
            {statusItem.description && (
              <p className="text-sm text-gray-600 mt-1">
                {statusItem.description}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
