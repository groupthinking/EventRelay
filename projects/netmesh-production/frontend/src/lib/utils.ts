import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// Utility functions for project management
export const formatDate = (date: string | Date): string => {
  const d = new Date(date);
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
};

export const getStatusColor = (status: string): string => {
  switch (status.toLowerCase()) {
    case 'active':
    case 'running':
    case 'completed':
      return 'bg-green-100 text-green-800 border-green-200';
    case 'pending':
    case 'waiting':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case 'failed':
    case 'error':
    case 'stopped':
      return 'bg-red-100 text-red-800 border-red-200';
    case 'paused':
    case 'suspended':
      return 'bg-gray-100 text-gray-800 border-gray-200';
    default:
      return 'bg-blue-100 text-blue-800 border-blue-200';
  }
};

export const getTypeIcon = (type: string): string => {
  switch (type.toLowerCase()) {
    case 'video':
    case 'video-analysis':
      return '🎥';
    case 'ai':
    case 'machine-learning':
      return '🤖';
    case 'web':
    case 'frontend':
      return '🌐';
    case 'api':
    case 'backend':
      return '⚙️';
    case 'mobile':
      return '📱';
    case 'desktop':
      return '💻';
    case 'data':
    case 'analytics':
      return '📊';
    case 'automation':
      return '🔄';
    default:
      return '📁';
  }
};

export const getStatusText = (status: string): string => {
  switch (status.toLowerCase()) {
    case 'active':
      return 'Active';
    case 'running':
      return 'Running';
    case 'completed':
      return 'Completed';
    case 'pending':
      return 'Pending';
    case 'waiting':
      return 'Waiting';
    case 'failed':
      return 'Failed';
    case 'error':
      return 'Error';
    case 'stopped':
      return 'Stopped';
    case 'paused':
      return 'Paused';
    case 'suspended':
      return 'Suspended';
    default:
      return status.charAt(0).toUpperCase() + status.slice(1);
  }
};

// Utility function for combining class names
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}