import React from 'react';

interface ProjectCardProps {
  projectName: string;
  status: 'Analyzing' | 'Deployed' | 'Failed' | 'Completed';
  timestamp: string;
}

const ProjectCard: React.FC<ProjectCardProps> = ({ projectName, status, timestamp }) => {
  const getStatusColor = () => {
    switch (status) {
      case 'Analyzing':
        return 'bg-blue-500';
      case 'Deployed':
        return 'bg-green-500';
      case 'Failed':
        return 'bg-red-500';
      case 'Completed':
        return 'bg-purple-500';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <div className="bg-white shadow-lg rounded-lg p-6 m-4 w-full md:w-1/3 lg:w-1/4 transition-transform transform hover:scale-105">
      <div className="flex justify-between items-start">
        <h3 className="text-xl font-bold text-gray-800">{projectName}</h3>
        <span className={`text-sm font-semibold text-white px-2 py-1 rounded-full ${getStatusColor()}`}>
          {status}
        </span>
      </div>
      <p className="text-gray-500 mt-4">{timestamp}</p>
    </div>
  );
};

export default ProjectCard;
