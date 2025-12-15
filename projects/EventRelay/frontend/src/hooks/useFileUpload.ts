import { useState, useCallback, useRef, useEffect } from 'react';

// File upload interfaces
export interface UploadFile {
  id: string;
  file: File;
  name: string;
  size: number;
  type: string;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  uploadedBytes: number;
  error?: string;
  uploadedAt?: Date;
  processedAt?: Date;
  url?: string;
  thumbnail?: string;
  metadata?: FileMetadata;
}

export interface FileMetadata {
  duration?: number; // for video/audio files
  dimensions?: { width: number; height: number }; // for image/video files
  format?: string;
  bitrate?: number;
  fps?: number; // for video files
  channels?: number; // for audio files
  sampleRate?: number; // for audio files
  codec?: string;
  size: number;
  lastModified: Date;
}

export interface UploadOptions {
  chunkSize?: number; // in bytes
  concurrentUploads?: number;
  retryAttempts?: number;
  retryDelay?: number; // in milliseconds
  validateFile?: (file: File) => boolean | string; // return error message if invalid
  onChunkUpload?: (chunk: Blob, chunkIndex: number, totalChunks: number) => Promise<void>;
  onProgress?: (fileId: string, progress: number) => void;
  onComplete?: (fileId: string, result: any) => void;
  onError?: (fileId: string, error: string) => void;
}

export interface UploadState {
  files: UploadFile[];
  isUploading: boolean;
  totalProgress: number;
  uploadProgress: Record<string, number>;
  activeUploads: number;
  completedUploads: number;
  failedUploads: number;
  totalSize: number;
  uploadedSize: number;
  error: string | null;
}

export interface UploadResult {
  fileId: string;
  success: boolean;
  url?: string;
  error?: string;
  metadata?: any;
}

export const useFileUpload = (options: UploadOptions = {}) => {
  const [state, setState] = useState<UploadState>({
    files: [],
    isUploading: false,
    totalProgress: 0,
    uploadProgress: {},
    activeUploads: 0,
    completedUploads: 0,
    failedUploads: 0,
    totalSize: 0,
    uploadedSize: 0,
    error: null,
  });

  const uploadQueueRef = useRef<UploadFile[]>([]);
  const activeUploadsRef = useRef<Set<string>>(new Set());
  const abortControllersRef = useRef<Map<string, AbortController>>(new Map());

  // Default options
  const defaultOptions: Required<UploadOptions> = {
    chunkSize: 1024 * 1024, // 1MB chunks
    concurrentUploads: 3,
    retryAttempts: 3,
    retryDelay: 1000,
    validateFile: () => true,
    onChunkUpload: async () => {},
    onProgress: () => {},
    onComplete: () => {},
    onError: () => {},
    ...options,
  };

  // Generate unique file ID
  const generateFileId = useCallback(() => {
    return `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  // Extract file metadata
  const extractFileMetadata = useCallback(async (file: File): Promise<FileMetadata> => {
    const metadata: FileMetadata = {
      size: file.size,
      lastModified: new Date(file.lastModified),
    };

    try {
      if (file.type.startsWith('video/')) {
        const video = document.createElement('video');
        video.preload = 'metadata';
        
        await new Promise((resolve, reject) => {
          video.onloadedmetadata = resolve;
          video.onerror = reject;
          video.src = URL.createObjectURL(file);
        });

        metadata.duration = video.duration;
        metadata.dimensions = { width: video.videoWidth, height: video.videoHeight };
        metadata.format = file.type.split('/')[1];
        
        URL.revokeObjectURL(video.src);
      } else if (file.type.startsWith('audio/')) {
        const audio = document.createElement('audio');
        audio.preload = 'metadata';
        
        await new Promise((resolve, reject) => {
          audio.onloadedmetadata = resolve;
          audio.onerror = reject;
          audio.src = URL.createObjectURL(file);
        });

        metadata.duration = audio.duration;
        metadata.format = file.type.split('/')[1];
        
        URL.revokeObjectURL(audio.src);
      } else if (file.type.startsWith('image/')) {
        const img = new Image();
        
        await new Promise((resolve, reject) => {
          img.onload = resolve;
          img.onerror = reject;
          img.src = URL.createObjectURL(file);
        });

        metadata.dimensions = { width: img.naturalWidth, height: img.naturalHeight };
        metadata.format = file.type.split('/')[1];
        
        URL.revokeObjectURL(img.src);
      }
    } catch (error) {
      console.warn('Failed to extract file metadata:', error);
    }

    return metadata;
  }, []);

  // Add files to upload queue
  const addFiles = useCallback(async (files: File[]) => {
    const uploadFiles: UploadFile[] = [];

    for (const file of files) {
      // Validate file
      const validation = defaultOptions.validateFile(file);
      if (validation !== true) {
        const errorMessage = typeof validation === 'string' ? validation : 'File validation failed';
        console.error(`File validation failed for ${file.name}:`, errorMessage);
        continue;
      }

      const fileId = generateFileId();
      const metadata = await extractFileMetadata(file);

      const uploadFile: UploadFile = {
        id: fileId,
        file,
        name: file.name,
        size: file.size,
        type: file.type,
        status: 'pending',
        progress: 0,
        uploadedBytes: 0,
        metadata,
      };

      uploadFiles.push(uploadFile);
    }

    setState(prev => {
      const newFiles = [...prev.files, ...uploadFiles];
      const totalSize = newFiles.reduce((sum, f) => sum + f.size, 0);
      
      return {
        ...prev,
        files: newFiles,
        totalSize,
      };
    });

    // Add to upload queue
    uploadQueueRef.current.push(...uploadFiles);

    // Start processing if not already uploading
    if (!state.isUploading) {
      processUploadQueue();
    }

    return uploadFiles;
  }, [defaultOptions.validateFile, generateFileId, extractFileMetadata, state.isUploading]);

  // Remove file from queue
  const removeFile = useCallback((fileId: string) => {
    // Cancel upload if in progress
    const controller = abortControllersRef.current.get(fileId);
    if (controller) {
      controller.abort();
      abortControllersRef.current.delete(fileId);
    }

    // Remove from active uploads
    activeUploadsRef.current.delete(fileId);

    setState(prev => {
      const newFiles = prev.files.filter(f => f.id !== fileId);
      const totalSize = newFiles.reduce((sum, f) => sum + f.size, 0);
      const uploadedSize = newFiles.reduce((sum, f) => sum + f.uploadedBytes, 0);
      
      return {
        ...prev,
        files: newFiles,
        totalSize,
        uploadedSize,
      };
    });

    // Remove from upload queue
    uploadQueueRef.current = uploadQueueRef.current.filter(f => f.id !== fileId);
  }, []);

  // Process upload queue
  const processUploadQueue = useCallback(async () => {
    if (state.isUploading || uploadQueueRef.current.length === 0) {
      return;
    }

    setState(prev => ({ ...prev, isUploading: true }));

    while (uploadQueueRef.current.length > 0 && activeUploadsRef.current.size < defaultOptions.concurrentUploads) {
      const file = uploadQueueRef.current.shift();
      if (file) {
        uploadFile(file);
      }
    }
  }, [state.isUploading, defaultOptions.concurrentUploads]);

  // Upload single file
  const uploadFile = useCallback(async (fileToUpload: UploadFile) => {
    const { file, id } = fileToUpload;
    
    // Create abort controller
    const abortController = new AbortController();
    abortControllersRef.current.set(id, abortController);

    // Add to active uploads
    activeUploadsRef.current.add(id);

    // Update file status
    setState(prev => ({
      ...prev,
      files: prev.files.map(f => 
        f.id === id ? { ...f, status: 'uploading' } : f
      ),
      activeUploads: prev.activeUploads + 1,
    }));

    try {
      // Calculate chunks
      const totalChunks = Math.ceil(file.size / defaultOptions.chunkSize);
      let uploadedChunks = 0;

      // Upload chunks
      for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
        if (abortController.signal.aborted) {
          throw new Error('Upload cancelled');
        }

        const start = chunkIndex * defaultOptions.chunkSize;
        const end = Math.min(start + defaultOptions.chunkSize, file.size);
        const chunk = file.slice(start, end);

        // Upload chunk
        await defaultOptions.onChunkUpload(chunk, chunkIndex, totalChunks);

        uploadedChunks++;
        const progress = (uploadedChunks / totalChunks) * 100;
        const uploadedBytes = Math.min(uploadedChunks * defaultOptions.chunkSize, file.size);

        // Update progress
        setState(prev => {
          const newFiles = prev.files.map(f => 
            f.id === id 
              ? { ...f, progress, uploadedBytes }
              : f
          );
          
          const totalUploadedSize = newFiles.reduce((sum, f) => sum + f.uploadedBytes, 0);
          const totalProgress = prev.totalSize > 0 ? (totalUploadedSize / prev.totalSize) * 100 : 0;
          
          return {
            ...prev,
            files: newFiles,
            uploadProgress: { ...prev.uploadProgress, [id]: progress },
            uploadedSize: totalUploadedSize,
            totalProgress: Math.round(totalProgress),
          };
        });

        // Call progress callback
        defaultOptions.onProgress(id, progress);
      }

      // Mark as completed
      setState(prev => ({
        ...prev,
        files: prev.files.map(f => 
          f.id === id 
            ? { ...f, status: 'completed', uploadedAt: new Date() }
            : f
        ),
        completedUploads: prev.completedUploads + 1,
        activeUploads: prev.activeUploads - 1,
      }));

      // Remove from active uploads
      activeUploadsRef.current.delete(id);
      abortControllersRef.current.delete(id);

      // Call completion callback
      defaultOptions.onComplete(id, { success: true, fileId: id });

      // Process next file in queue
      if (uploadQueueRef.current.length > 0) {
        const nextFile = uploadQueueRef.current.shift();
        if (nextFile) {
          uploadFile(nextFile);
        }
      }

      // Check if all uploads are complete
      if (activeUploadsRef.current.size === 0 && uploadQueueRef.current.length === 0) {
        setState(prev => ({ ...prev, isUploading: false }));
      }

    } catch (error: any) {
      // Handle upload error
      const errorMessage = error.name === 'AbortError' ? 'Upload cancelled' : error.message;

      setState(prev => ({
        ...prev,
        files: prev.files.map(f => 
          f.id === id 
            ? { ...f, status: 'failed', error: errorMessage }
            : f
        ),
        failedUploads: prev.failedUploads + 1,
        activeUploads: prev.activeUploads - 1,
        error: errorMessage,
      }));

      // Remove from active uploads
      activeUploadsRef.current.delete(id);
      abortControllersRef.current.delete(id);

      // Call error callback
      defaultOptions.onError(id, errorMessage);

      // Process next file in queue
      if (uploadQueueRef.current.length > 0) {
        const nextFile = uploadQueueRef.current.shift();
        if (nextFile) {
          uploadFile(nextFile);
        }
      }

      // Check if all uploads are complete
      if (activeUploadsRef.current.size === 0 && uploadQueueRef.current.length === 0) {
        setState(prev => ({ ...prev, isUploading: false }));
      }
    }
  }, [defaultOptions]);

  // Cancel upload
  const cancelUpload = useCallback((fileId: string) => {
    const controller = abortControllersRef.current.get(fileId);
    if (controller) {
      controller.abort();
      abortControllersRef.current.delete(fileId);
    }

    setState(prev => ({
      ...prev,
      files: prev.files.map(f => 
        f.id === fileId 
          ? { ...f, status: 'cancelled', progress: 0, uploadedBytes: 0 }
          : f
      ),
    }));
  }, []);

  // Retry failed upload
  const retryUpload = useCallback((fileId: string) => {
    setState(prev => {
      const newFiles = prev.files.map(f => 
        f.id === fileId 
          ? { ...f, status: 'pending' as const, progress: 0, uploadedBytes: 0, error: undefined }
          : f
      );
      
      return { ...prev, files: newFiles };
    });

    // Add back to queue
    const file = state.files.find(f => f.id === fileId);
    if (file) {
      uploadQueueRef.current.push(file);
      
      // Start processing if not already uploading
      if (!state.isUploading) {
        processUploadQueue();
      }
    }
  }, [state.files, state.isUploading, processUploadQueue]);

  // Clear completed uploads
  const clearCompleted = useCallback(() => {
    setState(prev => {
      const newFiles = prev.files.filter(f => f.status !== 'completed');
      const totalSize = newFiles.reduce((sum, f) => sum + f.size, 0);
      const uploadedSize = newFiles.reduce((sum, f) => sum + f.uploadedBytes, 0);
      
      return {
        ...prev,
        files: newFiles,
        totalSize,
        uploadedSize,
        completedUploads: 0,
      };
    });
  }, []);

  // Clear all uploads
  const clearAll = useCallback(() => {
    // Cancel all active uploads
    abortControllersRef.current.forEach(controller => controller.abort());
    abortControllersRef.current.clear();
    activeUploadsRef.current.clear();

    setState(prev => ({
      ...prev,
      files: [],
      isUploading: false,
      totalProgress: 0,
      uploadProgress: {},
      activeUploads: 0,
      completedUploads: 0,
      failedUploads: 0,
      totalSize: 0,
      uploadedSize: 0,
      error: null,
    }));

    uploadQueueRef.current = [];
  }, []);

  // Get upload statistics
  const getUploadStats = useCallback(() => {
    const total = state.files.length;
    const pending = state.files.filter(f => f.status === 'pending').length;
    const uploading = state.files.filter(f => f.status === 'uploading').length;
    const completed = state.files.filter(f => f.status === 'completed').length;
    const failed = state.files.filter(f => f.status === 'failed').length;
    const cancelled = state.files.filter(f => f.status === 'cancelled').length;

    return {
      total,
      pending,
      uploading,
      completed,
      failed,
      cancelled,
      successRate: total > 0 ? (completed / total) * 100 : 0,
      averageProgress: total > 0 
        ? state.files.reduce((sum, f) => sum + f.progress, 0) / total 
        : 0,
    };
  }, [state.files]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortControllersRef.current.forEach(controller => controller.abort());
      abortControllersRef.current.clear();
    };
  }, []);

  return {
    // State
    ...state,
    
    // Actions
    addFiles,
    removeFile,
    cancelUpload,
    retryUpload,
    clearCompleted,
    clearAll,
    
    // Utilities
    getUploadStats,
    processUploadQueue,
  };
};
