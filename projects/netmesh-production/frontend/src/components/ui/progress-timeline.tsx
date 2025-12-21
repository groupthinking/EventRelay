import React from 'react';
import { cn } from '../../lib/utils';

export interface TimelineEvent {
  id: string;
  title: string;
  description?: string;
  timestamp: Date;
  status: 'pending' | 'active' | 'completed' | 'failed' | 'skipped';
  icon?: React.ReactNode;
  duration?: number; // in milliseconds
  metadata?: Record<string, any>;
}

export interface ProgressTimelineProps {
  events: TimelineEvent[];
  currentEventIndex?: number;
  showTimestamps?: boolean;
  showDurations?: boolean;
  showMetadata?: boolean;
  animated?: boolean;
  className?: string;
  onEventClick?: (event: TimelineEvent, index: number) => void;
  clickable?: boolean;
  variant?: 'default' | 'compact' | 'detailed';
}

export function ProgressTimeline({
  events,
  currentEventIndex = 0,
  showTimestamps = true,
  showDurations = false,
  showMetadata = false,
  animated = true,
  className,
  onEventClick,
  clickable = false,
  variant = 'default'
}: ProgressTimelineProps) {
  const sortedEvents = [...events].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  
  const getEventStatusColor = (status: TimelineEvent['status']) => {
    const colors = {
      pending: 'border-gray-300 bg-gray-50 text-gray-500',
      active: 'border-blue-500 bg-blue-50 text-blue-600',
      completed: 'border-green-500 bg-green-50 text-green-600',
      failed: 'border-red-500 bg-red-50 text-red-600',
      skipped: 'border-yellow-500 bg-yellow-50 text-yellow-600'
    };
    return colors[status];
  };

  const getEventIcon = (event: TimelineEvent) => {
    if (event.icon) return event.icon;
    
    switch (event.status) {
      case 'completed':
        return (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        );
      case 'failed':
        return (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        );
      case 'active':
        return (
          <svg className="w-5 h-5 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
          </svg>
        );
      default:
        return (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
          </svg>
        );
    }
  };

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

  const formatDuration = (duration: number) => {
    const seconds = Math.floor(duration / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  };

  const handleEventClick = (event: TimelineEvent, index: number) => {
    if (clickable && onEventClick) {
      onEventClick(event, index);
    }
  };

  const variantConfig = {
    default: { showDescriptions: true, showMetadata: false },
    compact: { showDescriptions: false, showMetadata: false },
    detailed: { showDescriptions: true, showMetadata: true }
  };

  const config = variantConfig[variant];

  return (
    <div className={cn("w-full", className)}>
      <div className="relative">
        {/* Timeline Line */}
        <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-200" />
        
        {/* Events */}
        <div className="space-y-6">
          {sortedEvents.map((event, index) => {
            const isActive = index === currentEventIndex;
            const isCompleted = event.status === 'completed';
            const isFailed = event.status === 'failed';
            const isSkipped = event.status === 'skipped';
            
            return (
              <div
                key={event.id}
                className={cn(
                  "relative flex items-start gap-4",
                  clickable && "cursor-pointer hover:opacity-80 transition-opacity"
                )}
                onClick={() => handleEventClick(event, index)}
              >
                {/* Timeline Dot */}
                <div
                  className={cn(
                    "relative z-10 w-12 h-12 rounded-full border-2 flex items-center justify-center transition-all duration-300",
                    getEventStatusColor(event.status),
                    isActive && "ring-4 ring-offset-2 ring-blue-200",
                    animated && "transform hover:scale-110"
                  )}
                >
                  {getEventIcon(event)}
                </div>

                {/* Event Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <h4 className={cn(
                        "text-sm font-medium transition-colors duration-200",
                        isActive && "text-blue-700",
                        isCompleted && "text-green-700",
                        isFailed && "text-red-700",
                        isSkipped && "text-yellow-700",
                        event.status === 'pending' && "text-gray-600"
                      )}>
                        {event.title}
                      </h4>
                      
                      {/* Event Description */}
                      {config.showDescriptions && event.description && (
                        <p className={cn(
                          "text-sm text-gray-600 mt-1 line-clamp-2",
                          animated && "transition-all duration-200"
                        )}>
                          {event.description}
                        </p>
                      )}

                      {/* Event Metadata */}
                      {config.showMetadata && event.metadata && Object.keys(event.metadata).length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {Object.entries(event.metadata).map(([key, value]) => (
                            <span
                              key={key}
                              className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-gray-100 text-gray-700"
                            >
                              <span className="font-medium">{key}:</span>
                              <span className="ml-1">{String(value)}</span>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Event Details */}
                    <div className="flex flex-col items-end gap-2 text-right">
                      {/* Timestamp */}
                      {showTimestamps && (
                        <span className="text-xs text-gray-500 whitespace-nowrap">
                          {formatTimestamp(event.timestamp)}
                        </span>
                      )}
                      
                      {/* Duration */}
                      {showDurations && event.duration && (
                        <span className="text-xs text-gray-500">
                          {formatDuration(event.duration)}
                        </span>
                      )}
                      
                      {/* Status Badge */}
                      <span className={cn(
                        "text-xs px-2 py-1 rounded-full font-medium",
                        event.status === 'pending' && "bg-gray-100 text-gray-600",
                        event.status === 'active' && "bg-blue-100 text-blue-600",
                        event.status === 'completed' && "bg-green-100 text-green-600",
                        event.status === 'failed' && "bg-red-100 text-red-600",
                        event.status === 'skipped' && "bg-yellow-100 text-yellow-600"
                      )}>
                        {event.status.charAt(0).toUpperCase() + event.status.slice(1)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Timeline Summary */}
      <div className="mt-8 p-4 bg-gray-50 rounded-lg">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-medium text-gray-700">Timeline Summary</h4>
            <p className="text-xs text-gray-500 mt-1">
              {sortedEvents.length} events • {sortedEvents.filter(e => e.status === 'completed').length} completed
            </p>
          </div>
          <div className="text-right">
            <div className="text-sm font-medium text-gray-900">
              {sortedEvents.length > 0 && (
                <>
                  Started: {formatTimestamp(sortedEvents[0].timestamp)}
                </>
              )}
            </div>
            {sortedEvents.length > 1 && (
              <div className="text-xs text-gray-500">
                Duration: {formatDuration(
                  sortedEvents[sortedEvents.length - 1].timestamp.getTime() - sortedEvents[0].timestamp.getTime()
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Enhanced Progress Timeline with more features
export interface EnhancedProgressTimelineProps extends ProgressTimelineProps {
  showProgressBar?: boolean;
  showEventCount?: boolean;
  onTimelineComplete?: () => void;
  autoAdvance?: boolean;
  autoAdvanceInterval?: number;
}

export function EnhancedProgressTimeline({
  events,
  showProgressBar = true,
  showEventCount = true,
  onTimelineComplete,
  autoAdvance = false,
  autoAdvanceInterval = 5000,
  ...props
}: EnhancedProgressTimelineProps) {
  const [currentIndex, setCurrentIndex] = React.useState(props.currentEventIndex || 0);
  const completedEvents = events.filter(event => event.status === 'completed');
  const progress = events.length > 0 ? (completedEvents.length / events.length) * 100 : 0;

  React.useEffect(() => {
    if (autoAdvance && currentIndex < events.length - 1) {
      const timer = setInterval(() => {
        setCurrentIndex(prev => {
          if (prev < events.length - 1) {
            return prev + 1;
          }
          return prev;
        });
      }, autoAdvanceInterval);

      return () => clearInterval(timer);
    }
  }, [autoAdvance, autoAdvanceInterval, currentIndex, events.length]);

  React.useEffect(() => {
    if (progress >= 100 && onTimelineComplete) {
      onTimelineComplete();
    }
  }, [progress, onTimelineComplete]);

  return (
    <div className="space-y-6">
      {/* Progress Bar */}
      {showProgressBar && (
        <div className="w-full">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-gray-700">Timeline Progress</span>
            <span className="text-sm text-gray-500">{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Event Count */}
      {showEventCount && (
        <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
          <span className="text-sm font-medium text-blue-700">Current Event</span>
          <span className="text-sm text-blue-600">
            {currentIndex + 1} of {events.length}
          </span>
        </div>
      )}

      {/* Timeline */}
      <ProgressTimeline
        events={events}
        currentEventIndex={currentIndex}
        {...props}
      />
    </div>
  );
}
