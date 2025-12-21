'use client';

import React from 'react';
import { cn } from '../../lib/utils';

interface NoDataMessageProps {
  title?: string;
  message?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

const NoDataMessage: React.FC<NoDataMessageProps> = ({ 
  title = 'No data available',
  message = 'There are no items to display at the moment.',
  icon,
  action,
  className 
}) => {
  return (
    <div className={cn("flex flex-col items-center justify-center min-h-[200px] p-6 text-center", className)}>
      {icon && (
        <div className="text-gray-400 text-6xl mb-4">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        {title}
      </h3>
      <p className="text-gray-600 mb-4 max-w-md">
        {message}
      </p>
      {action && (
        <div className="mt-4">
          {action}
        </div>
      )}
    </div>
  );
};

export default NoDataMessage;
