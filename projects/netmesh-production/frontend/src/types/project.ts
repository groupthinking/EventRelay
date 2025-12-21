export interface Project {
  id: string;
  name: string;
  status: 'analyzing' | 'processing' | 'deployed' | 'failed' | 'pending';
  createdAt: string;
  updatedAt: string;
  description?: string;
  progress?: number;
  type: 'video-analysis' | 'file-upload' | 'api-integration';
}

export interface ProjectCardProps {
  project: Project;
  onClick?: (project: Project) => void;
}

export interface DashboardProps {
  projects?: Project[];
  isLoading?: boolean;
}

export interface ProjectFilters {
  status?: Project['status'];
  type?: Project['type'];
  dateRange?: {
    start: string;
    end: string;
  };
  search?: string;
}

export interface ProjectStats {
  total: number;
  analyzing: number;
  processing: number;
  deployed: number;
  failed: number;
  pending: number;
}
