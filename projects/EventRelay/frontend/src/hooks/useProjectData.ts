import { useState, useCallback, useEffect, useRef } from 'react';

// Project data interfaces
export interface Project {
  id: string;
  name: string;
  description: string;
  status: 'draft' | 'active' | 'completed' | 'archived';
  createdAt: Date;
  updatedAt: Date;
  tags: string[];
  priority: 'low' | 'medium' | 'high' | 'urgent';
  estimatedDuration: number; // in hours
  actualDuration: number; // in hours
  progress: number; // 0-100
  videoIds: string[];
  notes: ProjectNote[];
  collaborators: string[];
  dueDate?: Date;
  completedAt?: Date;
}

export interface ProjectNote {
  id: string;
  content: string;
  timestamp: Date;
  type: 'general' | 'insight' | 'question' | 'action';
  tags: string[];
}

export interface LearningProgress {
  videoId: string;
  projectId: string;
  watchedSegments: TimeRange[];
  completedChapters: string[];
  notes: LearningNote[];
  exerciseScores: ExerciseScore[];
  lastPosition: number;
  totalWatchTime: number;
  completionPercentage: number;
  lastAccessed: Date;
  timeSpent: number; // in minutes
}

export interface TimeRange {
  start: number;
  end: number;
  duration: number;
}

export interface LearningNote {
  id: string;
  content: string;
  timestamp: number;
  chapterId?: string;
  tags: string[];
  type: 'insight' | 'question' | 'todo' | 'highlight';
}

export interface ExerciseScore {
  exerciseId: string;
  score: number;
  maxScore: number;
  completedAt: Date;
  timeSpent: number;
}

export interface ProjectDataState {
  projects: Project[];
  currentProject: Project | null;
  learningProgress: Map<string, LearningProgress>;
  isLoading: boolean;
  error: string | null;
  filters: ProjectFilters;
  sortBy: ProjectSortOption;
  searchQuery: string;
}

export interface ProjectFilters {
  status: Project['status'][];
  priority: Project['priority'][];
  tags: string[];
  dateRange: {
    start: Date | null;
    end: Date | null;
  };
}

export type ProjectSortOption = 
  | 'name' 
  | 'createdAt' 
  | 'updatedAt' 
  | 'priority' 
  | 'progress' 
  | 'dueDate';

export const useProjectData = () => {
  const [state, setState] = useState<ProjectDataState>({
    projects: [],
    currentProject: null,
    learningProgress: new Map(),
    isLoading: false,
    error: null,
    filters: {
      status: [],
      priority: [],
      tags: [],
      dateRange: { start: null, end: null },
    },
    sortBy: 'updatedAt',
    searchQuery: '',
  });

  const projectsRef = useRef<Project[]>([]);
  const progressRef = useRef<Map<string, LearningProgress>>(new Map());

  // Load projects from localStorage on mount
  useEffect(() => {
    try {
      const savedProjects = localStorage.getItem('uvai_projects');
      const savedProgress = localStorage.getItem('uvai_learning_progress');
      
      if (savedProjects) {
        const projects = JSON.parse(savedProjects).map((p: any) => ({
          ...p,
          createdAt: new Date(p.createdAt),
          updatedAt: new Date(p.updatedAt),
          dueDate: p.dueDate ? new Date(p.dueDate) : undefined,
          completedAt: p.completedAt ? new Date(p.completedAt) : undefined,
        }));
        setState(prev => ({ ...prev, projects }));
        projectsRef.current = projects;
      }
      
      if (savedProgress) {
        const progressData = JSON.parse(savedProgress) as [string, LearningProgress][];
        const progress = new Map<string, LearningProgress>(progressData);
        setState(prev => ({ ...prev, learningProgress: progress }));
        progressRef.current = progress;
      }
    } catch (error) {
      console.error('Failed to load project data:', error);
    }
  }, []);

  // Save projects to localStorage whenever they change
  useEffect(() => {
    if (projectsRef.current.length > 0) {
      localStorage.setItem('uvai_projects', JSON.stringify(projectsRef.current));
    }
  }, [state.projects]);

  // Save learning progress to localStorage whenever it changes
  useEffect(() => {
    if (progressRef.current.size > 0) {
      const progressArray = Array.from(progressRef.current.entries());
      localStorage.setItem('uvai_learning_progress', JSON.stringify(progressArray));
    }
  }, [state.learningProgress]);

  // Create new project
  const createProject = useCallback((projectData: Omit<Project, 'id' | 'createdAt' | 'updatedAt'>) => {
    const newProject: Project = {
      ...projectData,
      id: `project_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      createdAt: new Date(),
      updatedAt: new Date(),
      progress: 0,
      actualDuration: 0,
    };

    setState(prev => {
      const updatedProjects = [...prev.projects, newProject];
      projectsRef.current = updatedProjects;
      return { ...prev, projects: updatedProjects };
    });

    return newProject;
  }, []);

  // Update project
  const updateProject = useCallback((projectId: string, updates: Partial<Project>) => {
    setState(prev => {
      const updatedProjects = prev.projects.map(project =>
        project.id === projectId
          ? { ...project, ...updates, updatedAt: new Date() }
          : project
      );
      projectsRef.current = updatedProjects;
      return { ...prev, projects: updatedProjects };
    });
  }, []);

  // Delete project
  const deleteProject = useCallback((projectId: string) => {
    setState(prev => {
      const updatedProjects = prev.projects.filter(p => p.id !== projectId);
      projectsRef.current = updatedProjects;
      
      // Clear current project if it was deleted
      const currentProject = prev.currentProject?.id === projectId ? null : prev.currentProject;
      
      return { 
        ...prev, 
        projects: updatedProjects, 
        currentProject 
      };
    });
  }, []);

  // Set current project
  const setCurrentProject = useCallback((project: Project | null) => {
    setState(prev => ({ ...prev, currentProject: project }));
  }, []);

  // Update learning progress
  const updateLearningProgress = useCallback((
    videoId: string, 
    projectId: string, 
    updates: Partial<LearningProgress>
  ) => {
    setState(prev => {
      const progressKey = `${projectId}_${videoId}`;
      const existingProgress = prev.learningProgress.get(progressKey);
      
      const updatedProgress = new Map(prev.learningProgress);
      updatedProgress.set(progressKey, {
        ...existingProgress,
        videoId,
        projectId,
        lastAccessed: new Date(),
        ...updates,
      } as LearningProgress);
      
      progressRef.current = updatedProgress;
      return { ...prev, learningProgress: updatedProgress };
    });
  }, []);

  // Add note to project
  const addProjectNote = useCallback((projectId: string, note: Omit<ProjectNote, 'id' | 'timestamp'>) => {
    const newNote: ProjectNote = {
      ...note,
      id: `note_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
    };

    setState(prev => {
      const updatedProjects = prev.projects.map(project =>
        project.id === projectId
          ? { ...project, notes: [...project.notes, newNote] }
          : project
      );
      projectsRef.current = updatedProjects;
      return { ...prev, projects: updatedProjects };
    });

    return newNote;
  }, []);

  // Add learning note
  const addLearningNote = useCallback((
    videoId: string, 
    projectId: string, 
    note: Omit<LearningNote, 'id'>
  ) => {
    const newNote: LearningNote = {
      ...note,
      id: `learning_note_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    };

    updateLearningProgress(videoId, projectId, {
      notes: [...(state.learningProgress.get(`${projectId}_${videoId}`)?.notes || []), newNote],
    });

    return newNote;
  }, [state.learningProgress, updateLearningProgress]);

  // Update project progress
  const updateProjectProgress = useCallback((projectId: string, progress: number) => {
    updateProject(projectId, { progress: Math.max(0, Math.min(100, progress)) });
  }, [updateProject]);

  // Filter projects
  const filterProjects = useCallback((filters: Partial<ProjectFilters>) => {
    setState(prev => ({ ...prev, filters: { ...prev.filters, ...filters } }));
  }, []);

  // Sort projects
  const sortProjects = useCallback((sortBy: ProjectSortOption) => {
    setState(prev => ({ ...prev, sortBy }));
  }, []);

  // Search projects
  const searchProjects = useCallback((query: string) => {
    setState(prev => ({ ...prev, searchQuery: query }));
  }, []);

  // Get filtered and sorted projects
  const getFilteredProjects = useCallback(() => {
    let filtered = [...state.projects];

    // Apply filters
    if (state.filters.status.length > 0) {
      filtered = filtered.filter(p => state.filters.status.includes(p.status));
    }
    if (state.filters.priority.length > 0) {
      filtered = filtered.filter(p => state.filters.priority.includes(p.priority));
    }
    if (state.filters.tags.length > 0) {
      filtered = filtered.filter(p => 
        state.filters.tags.some(tag => p.tags.includes(tag))
      );
    }
    if (state.filters.dateRange.start || state.filters.dateRange.end) {
      filtered = filtered.filter(p => {
        const projectDate = p.updatedAt;
        if (state.filters.dateRange.start && projectDate < state.filters.dateRange.start) {
          return false;
        }
        if (state.filters.dateRange.end && projectDate > state.filters.dateRange.end) {
          return false;
        }
        return true;
      });
    }

    // Apply search
    if (state.searchQuery) {
      const query = state.searchQuery.toLowerCase();
      filtered = filtered.filter(p =>
        p.name.toLowerCase().includes(query) ||
        p.description.toLowerCase().includes(query) ||
        p.tags.some(tag => tag.toLowerCase().includes(query))
      );
    }

    // Apply sorting
    filtered.sort((a, b) => {
      switch (state.sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'createdAt':
          return b.createdAt.getTime() - a.createdAt.getTime();
        case 'updatedAt':
          return b.updatedAt.getTime() - a.updatedAt.getTime();
        case 'priority':
          const priorityOrder = { urgent: 4, high: 3, medium: 2, low: 1 };
          return priorityOrder[b.priority] - priorityOrder[a.priority];
        case 'progress':
          return b.progress - a.progress;
        case 'dueDate':
          if (!a.dueDate && !b.dueDate) return 0;
          if (!a.dueDate) return 1;
          if (!b.dueDate) return -1;
          return a.dueDate.getTime() - b.dueDate.getTime();
        default:
          return 0;
      }
    });

    return filtered;
  }, [state.projects, state.filters, state.sortBy, state.searchQuery]);

  // Get project statistics
  const getProjectStats = useCallback(() => {
    const total = state.projects.length;
    const completed = state.projects.filter(p => p.status === 'completed').length;
    const active = state.projects.filter(p => p.status === 'active').length;
    const draft = state.projects.filter(p => p.status === 'draft').length;
    const archived = state.projects.filter(p => p.status === 'archived').length;
    
    const totalProgress = state.projects.reduce((sum, p) => sum + p.progress, 0);
    const averageProgress = total > 0 ? totalProgress / total : 0;
    
    const totalEstimatedHours = state.projects.reduce((sum, p) => sum + p.estimatedDuration, 0);
    const totalActualHours = state.projects.reduce((sum, p) => sum + p.actualDuration, 0);

    return {
      total,
      completed,
      active,
      draft,
      archived,
      averageProgress: Math.round(averageProgress),
      totalEstimatedHours,
      totalActualHours,
      completionRate: total > 0 ? (completed / total) * 100 : 0,
    };
  }, [state.projects]);

  // Export project data
  const exportProjectData = useCallback(() => {
    const data = {
      projects: state.projects,
      learningProgress: Array.from(state.learningProgress.entries()),
      exportDate: new Date().toISOString(),
      version: '1.0.0',
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `uvai_project_data_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [state.projects, state.learningProgress]);

  // Import project data
  const importProjectData = useCallback(async (file: File) => {
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      
      if (data.projects && Array.isArray(data.projects)) {
        const projects = data.projects.map((p: any) => ({
          ...p,
          createdAt: new Date(p.createdAt),
          updatedAt: new Date(p.updatedAt),
          dueDate: p.dueDate ? new Date(p.dueDate) : undefined,
          completedAt: p.completedAt ? new Date(p.completedAt) : undefined,
        }));
        
        setState(prev => {
          projectsRef.current = projects;
          return { ...prev, projects };
        });
      }
      
      if (data.learningProgress && Array.isArray(data.learningProgress)) {
        const progressData = data.learningProgress as [string, LearningProgress][];
        const progress = new Map<string, LearningProgress>(progressData);
        setState(prev => {
          progressRef.current = progress;
          return { ...prev, learningProgress: progress };
        });
      }
      
      return true;
    } catch (error) {
      console.error('Failed to import project data:', error);
      return false;
    }
  }, []);

  return {
    // State
    ...state,
    
    // Actions
    createProject,
    updateProject,
    deleteProject,
    setCurrentProject,
    updateLearningProgress,
    addProjectNote,
    addLearningNote,
    updateProjectProgress,
    
    // Filtering and sorting
    filterProjects,
    sortProjects,
    searchProjects,
    getFilteredProjects,
    
    // Analytics
    getProjectStats,
    
    // Data management
    exportProjectData,
    importProjectData,
  };
};
