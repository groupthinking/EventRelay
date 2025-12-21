import React from 'react';

interface ProgressBarProps {
  currentStep: number;
  totalSteps: number;
  statusText: string;
}

const ProgressBar: React.FC<ProgressBarProps> = ({ currentStep, totalSteps, statusText }) => {
  const progressPercentage = (currentStep / totalSteps) * 100;

  return (
    <div className="w-full bg-gray-200 rounded-full my-4">
      <div
        className="bg-blue-600 text-xs font-medium text-blue-100 text-center p-0.5 leading-none rounded-full transition-all duration-500"
        style={{ width: `${progressPercentage}%` }}
      >
        {statusText}
      </div>
    </div>
  );
};

export default ProgressBar;
