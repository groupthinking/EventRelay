import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { formatDate, getStatusColor, getTypeIcon, getStatusText } from "../../lib/utils";
import { ProjectCardProps } from "../../types/project";

export function ProjectCard({ project, onClick }: ProjectCardProps) {
  const handleClick = () => {
    onClick?.(project);
  };

  return (
    <Card onClick={handleClick} className="group">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{getTypeIcon(project.type)}</span>
            <div>
              <CardTitle className="group-hover:text-blue-600 transition-colors">
                {project.name}
              </CardTitle>
              {project.description && (
                <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                  {project.description}
                </p>
              )}
            </div>
          </div>
          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(project.status)}`}
          >
            {getStatusText(project.status)}
          </span>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="flex items-center justify-between text-sm text-gray-500">
          <div className="flex items-center gap-4">
            <span>Created {formatDate(project.createdAt)}</span>
            {project.updatedAt !== project.createdAt && (
              <span>Updated {formatDate(project.updatedAt)}</span>
            )}
          </div>
          
          {project.progress !== undefined && (
            <div className="flex items-center gap-2">
              <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${project.progress}%` }}
                />
              </div>
              <span className="text-xs font-medium">{project.progress}%</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
