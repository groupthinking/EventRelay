// Enhanced Video Analysis Hook
export { useVideoAnalysis } from './useVideoAnalysis';
export type {
  VideoMetadata,
  AnalysisResult,
  Chapter,
  VideoAnalysisState,
  AnalysisOptions,
} from './useVideoAnalysis';

// Enhanced Project Data Hook
export { useProjectData } from './useProjectData';
export type {
  Project,
  ProjectNote,
  LearningProgress,
  TimeRange,
  LearningNote,
  ExerciseScore,
  ProjectDataState,
  ProjectFilters,
  ProjectSortOption,
} from './useProjectData';

// Enhanced File Upload Hook
export { useFileUpload } from './useFileUpload';
export type {
  UploadFile,
  FileMetadata,
  UploadOptions,
  UploadState,
  UploadResult,
} from './useFileUpload';

// Enhanced MCP Integration Hook
export { useMCPIntegration } from './useMCPIntegration';
export type {
  AgentStatus,
  SystemMetrics,
  ChatMessage,
  VideoProcessingOptions,
  VideoProcessingResult,
  MCPIntegrationState,
  MCPIntegrationOptions,
} from './useMCPIntegration';

// Enhanced Local Storage Hook
export { useLocalStorage } from './useLocalStorage';
export type {
  StorageItem,
  StorageOptions,
  StorageState,
} from './useLocalStorage';

// Enhanced Debounce Hooks
export {
  useDebounce,
  useDebouncedCallback,
  useDebouncedState,
  useDebouncedEffect,
  useDebouncedAsyncCallback,
  useDebouncedSearch,
  useDebouncedForm,
} from './useDebounce';
export type {
  DebounceOptions,
  DebouncedFunction,
} from './useDebounce';
