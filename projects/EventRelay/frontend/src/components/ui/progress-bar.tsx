import { cn } from "../../lib/utils";
import { ReactNode } from "react";

export interface ProgressBarProps {
  currentStep: number;
  totalSteps: number;
  status?: 'analyzing' | 'processing' | 'deployed' | 'failed' | 'pending';
  animated?: boolean;
  showSteps?: boolean;
  stepLabels?: string[];
  className?: string;
}

export function ProgressBar({
  currentStep,
  totalSteps,
  status = 'pending',
  animated = true,
  showSteps = false,
  stepLabels = [],
  className
}: ProgressBarProps) {
  const progress = Math.min((currentStep / totalSteps) * 100, 100);
  
  const getStatusColor = (status: string) => {
    const colors = {
      analyzing: 'bg-blue-500',
      processing: 'bg-yellow-500',
      deployed: 'bg-green-500',
      failed: 'bg-red-500',
      pending: 'bg-gray-400'
    };
    return colors[status as keyof typeof colors] || colors.pending;
  };

  const getStatusBgColor = (status: string) => {
    const colors = {
      analyzing: 'bg-blue-100',
      processing: 'bg-yellow-100',
      deployed: 'bg-green-100',
      failed: 'bg-red-100',
      pending: 'bg-gray-100'
    };
    return colors[status as keyof typeof colors] || colors.pending;
  };

  const getStatusTextColor = (status: string) => {
    const colors = {
      analyzing: 'text-blue-700',
      processing: 'text-yellow-700',
      deployed: 'text-green-700',
      failed: 'text-red-700',
      pending: 'text-gray-700'
    };
    return colors[status as keyof typeof colors] || colors.pending;
  };

  return (
    <div className={cn("w-full", className)}>
      {/* Main Progress Bar */}
      <div className="relative">
        <div className={cn(
          "h-3 bg-gray-200 rounded-full overflow-hidden",
          getStatusBgColor(status)
        )}>
          <div
            className={cn(
              "h-full rounded-full transition-all duration-1000 ease-out",
              getStatusColor(status),
              animated && "animate-pulse"
            )}
            style={{ 
              width: `${progress}%`,
              transition: animated ? 'width 1s ease-out' : 'none'
            }}
          />
        </div>
        
        {/* Progress Percentage */}
        <div className="absolute -top-8 right-0">
          <span className={cn(
            "text-sm font-medium px-2 py-1 rounded-md",
            getStatusBgColor(status),
            getStatusTextColor(status)
          )}>
            {Math.round(progress)}%
          </span>
        </div>
      </div>

      {/* Step Indicators */}
      {showSteps && totalSteps > 1 && (
        <div className="mt-4">
          <div className="flex justify-between items-center">
            {Array.from({ length: totalSteps }, (_, index) => {
              const isCompleted = index < currentStep;
              const isCurrent = index === currentStep - 1;
              const stepNumber = index + 1;
              
              return (
                <div key={index} className="flex flex-col items-center">
                  {/* Step Circle */}
                  <div className={cn(
                    "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium border-2 transition-all duration-300",
                    isCompleted && getStatusColor(status),
                    isCurrent && "ring-4 ring-offset-2",
                    isCurrent && getStatusColor(status).replace('bg-', 'ring-'),
                    !isCompleted && "bg-white border-gray-300 text-gray-500",
                    isCompleted && "text-white border-transparent"
                  )}>
                    {isCompleted ? (
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    ) : (
                      stepNumber
                    )}
                  </div>
                  
                  {/* Step Label */}
                  {stepLabels[index] && (
                    <span className={cn(
                      "text-xs mt-2 text-center max-w-20",
                      isCompleted ? getStatusTextColor(status) : "text-gray-500",
                      "line-clamp-2"
                    )}>
                      {stepLabels[index]}
                    </span>
                  )}
                  
                  {/* Connecting Line */}
                  {index < totalSteps - 1 && (
                    <div className={cn(
                      "absolute w-full h-0.5 transition-all duration-300",
                      isCompleted ? getStatusColor(status) : "bg-gray-300",
                      "top-4 left-1/2 transform -translate-y-1/2"
                    )} />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Status Text */}
      <div className="mt-3 text-center">
        <span className={cn(
          "text-sm font-medium",
          getStatusTextColor(status)
        )}>
          {status.charAt(0).toUpperCase() + status.slice(1)}...
        </span>
        {currentStep > 0 && (
          <span className="text-gray-500 ml-2">
            Step {currentStep} of {totalSteps}
          </span>
        )}
      </div>
    </div>
  );
}

// Enhanced Progress Bar with more features
export interface EnhancedProgressBarProps extends ProgressBarProps {
  showETA?: boolean;
  speed?: 'slow' | 'normal' | 'fast';
  onStepComplete?: (step: number) => void;
}

export function EnhancedProgressBar({
  currentStep,
  totalSteps,
  status = 'pending',
  animated = true,
  showSteps = true,
  stepLabels = [],
  showETA = false,
  speed = 'normal',
  onStepComplete,
  className
}: EnhancedProgressBarProps) {
  const speedMultiplier = {
    slow: 0.5,
    normal: 1,
    fast: 2
  };

  const estimatedTimePerStep = {
    slow: 5000,    // 5 seconds
    normal: 3000,  // 3 seconds
    fast: 1500     // 1.5 seconds
  };

  const remainingSteps = totalSteps - currentStep;
  const estimatedTimeRemaining = Math.round(
    (remainingSteps * estimatedTimePerStep[speed]) / 1000
  );

  return (
    <div className={cn("w-full", className)}>
      <ProgressBar
        currentStep={currentStep}
        totalSteps={totalSteps}
        status={status}
        animated={animated}
        showSteps={showSteps}
        stepLabels={stepLabels}
      />
      
      {/* ETA Display */}
      {showETA && remainingSteps > 0 && (
        <div className="mt-4 p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Estimated time remaining:</span>
            <span className="font-medium text-gray-900">
              {estimatedTimeRemaining > 60 
                ? `${Math.floor(estimatedTimeRemaining / 60)}m ${estimatedTimeRemaining % 60}s`
                : `${estimatedTimeRemaining}s`
              }
            </span>
          </div>
          
          {/* Speed Indicator */}
          <div className="mt-2 flex items-center gap-2">
            <span className="text-xs text-gray-500">Speed:</span>
            <span className={cn(
              "text-xs px-2 py-1 rounded-full",
              speed === 'fast' && "bg-green-100 text-green-700",
              speed === 'normal' && "bg-blue-100 text-blue-700",
              speed === 'slow' && "bg-yellow-100 text-yellow-700"
            )}>
              {speed.charAt(0).toUpperCase() + speed.slice(1)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
