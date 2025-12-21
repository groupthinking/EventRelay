import React from 'react';
import { cn } from '../../lib/utils';

export interface ProgressStep {
  id: string;
  label: string;
  description?: string;
  status: 'pending' | 'active' | 'completed' | 'failed' | 'skipped';
  icon?: React.ReactNode;
  duration?: number; // in milliseconds
  errorMessage?: string;
}

export interface ProgressStepsProps {
  steps: ProgressStep[];
  currentStepIndex: number;
  showStepNumbers?: boolean;
  showStepDescriptions?: boolean;
  showStepDurations?: boolean;
  showStepErrors?: boolean;
  animated?: boolean;
  className?: string;
  onStepClick?: (stepIndex: number) => void;
  clickable?: boolean;
}

export function ProgressSteps({
  steps,
  currentStepIndex,
  showStepNumbers = true,
  showStepDescriptions = true,
  showStepDurations = false,
  showStepErrors = true,
  animated = true,
  className,
  onStepClick,
  clickable = false
}: ProgressStepsProps) {
  const getStepStatusColor = (status: ProgressStep['status']) => {
    const colors = {
      pending: 'border-gray-300 bg-gray-50 text-gray-500',
      active: 'border-blue-500 bg-blue-50 text-blue-600',
      completed: 'border-green-500 bg-green-50 text-green-600',
      failed: 'border-red-500 bg-red-50 text-red-600',
      skipped: 'border-yellow-500 bg-yellow-50 text-yellow-600'
    };
    return colors[status];
  };

  const getStepIcon = (step: ProgressStep, index: number) => {
    if (step.icon) return step.icon;
    
    switch (step.status) {
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
      case 'skipped':
        return (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        );
      default:
        return showStepNumbers ? (
          <span className="text-sm font-medium">{index + 1}</span>
        ) : null;
    }
  };

  const getStepBorderColor = (status: ProgressStep['status']) => {
    const colors = {
      pending: 'border-gray-300',
      active: 'border-blue-500',
      completed: 'border-green-500',
      failed: 'border-red-500',
      skipped: 'border-yellow-500'
    };
    return colors[status];
  };

  const handleStepClick = (stepIndex: number) => {
    if (clickable && onStepClick) {
      onStepClick(stepIndex);
    }
  };

  return (
    <div className={cn("w-full", className)}>
      <div className="relative">
        {/* Progress Line */}
        <div className="absolute top-6 left-0 right-0 h-0.5 bg-gray-200 -z-10" />
        
        {/* Steps */}
        <div className="flex justify-between">
          {steps.map((step, index) => {
            const isActive = index === currentStepIndex;
            const isCompleted = step.status === 'completed';
            const isFailed = step.status === 'failed';
            const isSkipped = step.status === 'skipped';
            
            return (
              <div
                key={step.id}
                className={cn(
                  "flex flex-col items-center relative",
                  clickable && "cursor-pointer hover:opacity-80 transition-opacity"
                )}
                onClick={() => handleStepClick(index)}
              >
                {/* Step Circle */}
                <div
                  className={cn(
                    "w-12 h-12 rounded-full border-2 flex items-center justify-center transition-all duration-300",
                    getStepStatusColor(step.status),
                    isActive && "ring-4 ring-offset-2 ring-blue-200",
                    animated && "transform hover:scale-110"
                  )}
                >
                  {getStepIcon(step, index)}
                </div>

                {/* Step Label */}
                <div className="mt-3 text-center max-w-24">
                  <div className={cn(
                    "text-sm font-medium transition-colors duration-200",
                    isActive && "text-blue-700",
                    isCompleted && "text-green-700",
                    isFailed && "text-red-700",
                    isSkipped && "text-yellow-700",
                    step.status === 'pending' && "text-gray-600"
                  )}>
                    {step.label}
                  </div>
                  
                  {/* Step Description */}
                  {showStepDescriptions && step.description && (
                    <div className={cn(
                      "text-xs mt-1 text-gray-500 line-clamp-2",
                      animated && "transition-all duration-200"
                    )}>
                      {step.description}
                    </div>
                  )}
                </div>

                {/* Step Duration */}
                {showStepDurations && step.duration && (
                  <div className="mt-2 text-xs text-gray-400">
                    {Math.round(step.duration / 1000)}s
                  </div>
                )}

                {/* Error Message */}
                {showStepErrors && isFailed && step.errorMessage && (
                  <div className="absolute top-16 left-1/2 transform -translate-x-1/2 z-10">
                    <div className="bg-red-100 border border-red-300 text-red-700 px-3 py-2 rounded-lg text-xs max-w-32 text-center shadow-lg">
                      {step.errorMessage}
                      <div className="absolute -top-1 left-1/2 transform -translate-x-1/2 w-2 h-2 bg-red-100 border-l border-t border-red-300 rotate-45" />
                    </div>
                  </div>
                )}

                {/* Progress Line Segment */}
                {index < steps.length - 1 && (
                  <div
                    className={cn(
                      "absolute top-6 left-1/2 w-full h-0.5 transition-all duration-500",
                      isCompleted ? "bg-green-500" : "bg-gray-200"
                    )}
                    style={{ width: 'calc(100% + 3rem)' }}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Current Step Info */}
      {steps[currentStepIndex] && (
        <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
              </svg>
            </div>
            <div>
              <div className="font-medium text-blue-900">
                Currently: {steps[currentStepIndex].label}
              </div>
              {steps[currentStepIndex].description && (
                <div className="text-sm text-blue-700">
                  {steps[currentStepIndex].description}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Enhanced Progress Steps with more features
export interface EnhancedProgressStepsProps extends ProgressStepsProps {
  showProgressBar?: boolean;
  showStepTiming?: boolean;
  onStepHover?: (stepIndex: number) => void;
  onStepLeave?: () => void;
}

export function EnhancedProgressSteps({
  steps,
  currentStepIndex,
  showProgressBar = true,
  showStepTiming = true,
  onStepHover,
  onStepLeave,
  ...props
}: EnhancedProgressStepsProps) {
  const totalSteps = steps.length;
  const completedSteps = steps.filter(step => step.status === 'completed').length;
  const progress = (completedSteps / totalSteps) * 100;

  return (
    <div className="space-y-6">
      {/* Progress Bar */}
      {showProgressBar && (
        <div className="w-full">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-gray-700">Overall Progress</span>
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

      {/* Steps */}
      <ProgressSteps
        steps={steps}
        currentStepIndex={currentStepIndex}
        {...props}
      />

      {/* Step Timing Information */}
      {showStepTiming && (
        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <h4 className="text-sm font-medium text-gray-700 mb-3">Step Timing</h4>
          <div className="space-y-2">
            {steps.map((step, index) => (
              <div key={step.id} className="flex justify-between items-center text-sm">
                <span className={cn(
                  "font-medium",
                  index === currentStepIndex ? "text-blue-600" : "text-gray-600"
                )}>
                  {step.label}
                </span>
                <span className="text-gray-500">
                  {step.duration ? `${Math.round(step.duration / 1000)}s` : 'Pending'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
