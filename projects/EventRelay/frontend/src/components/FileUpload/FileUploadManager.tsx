import React, { useState, useCallback, useMemo } from 'react';
import EnhancedFileUpload from './EnhancedFileUpload';
import VideoPreview from './VideoPreview';
import MediaGallery from './MediaGallery';
import { useFileUpload } from '../../hooks/useFileUpload';
import { ProgressSpinner } from '../ui/progress-spinner';

interface UploadedFile {
  id: string;
  file: File;
  uploadedAt: Date;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  progress?: number;
  error?: string;
  metadata?: {
    duration: number;
    width: number;
    height: number;
    size: number;
  };
}

interface FileUploadManagerProps {
  onFilesProcessed?: (files: UploadedFile[]) => void;
  onFileSelected?: (file: UploadedFile) => void;
  className?: string;
  maxFiles?: number;
  maxFileSize?: number;
  acceptedTypes?: string[];
  showGallery?: boolean;
  showUploadArea?: boolean;
  autoProcess?: boolean;
}

const FileUploadManager: React.FC<FileUploadManagerProps> = ({
  onFilesProcessed,
  onFileSelected,
  className = '',
  maxFiles = 50,
  maxFileSize = 500, // 500MB default
  acceptedTypes = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'],
  showGallery = true,
  showUploadArea = true,
  autoProcess = true
}) => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<UploadedFile | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [showUploadStats, setShowUploadStats] = useState(false);

  const {
    addFiles,
    uploadProgress,
    isUploading,
    error: uploadError,
    clearAll
  } = useFileUpload();

  // Generate unique ID for files
  const generateFileId = useCallback(() => {
    return `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  // Handle file upload completion
  const handleUploadComplete = useCallback((files: File[]) => {
    const newUploadedFiles: UploadedFile[] = files.map(file => ({
      id: generateFileId(),
      file,
      uploadedAt: new Date(),
      status: 'uploading',
      progress: 0
    }));

    setUploadedFiles(prev => [...prev, ...newUploadedFiles]);

    // Simulate processing if autoProcess is enabled
    if (autoProcess) {
      newUploadedFiles.forEach(fileItem => {
        simulateFileProcessing(fileItem.id);
      });
    }

    onFilesProcessed?.(newUploadedFiles);
  }, [generateFileId, autoProcess, onFilesProcessed]);

  // Handle upload error
  const handleUploadError = useCallback((error: string) => {
    console.error('Upload error:', error);
    // You could show a toast notification here
  }, []);

  // Simulate file processing (replace with actual processing logic)
  const simulateFileProcessing = useCallback((fileId: string) => {
    setUploadedFiles(prev => 
      prev.map(file => 
        file.id === fileId 
          ? { ...file, status: 'processing' as const }
          : file
      )
    );

    // Simulate processing time
    setTimeout(() => {
      setUploadedFiles(prev => 
        prev.map(file => 
          file.id === fileId 
            ? { 
                ...file, 
                status: 'completed' as const,
                metadata: {
                  duration: Math.random() * 600 + 60, // 1-11 minutes
                  width: Math.random() > 0.5 ? 1920 : 1280,
                  height: Math.random() > 0.5 ? 1080 : 720,
                  size: file.file.size
                }
              }
            : file
        )
      );
    }, 2000 + Math.random() * 3000); // 2-5 seconds
  }, []);

  // Handle file selection
  const handleFileSelect = useCallback((file: UploadedFile) => {
    setSelectedFile(file);
    onFileSelected?.(file);
  }, [onFileSelected]);

  // Handle file deletion
  const handleFileDelete = useCallback((fileId: string) => {
    setUploadedFiles(prev => prev.filter(file => file.id !== fileId));
    
    if (selectedFile?.id === fileId) {
      setSelectedFile(null);
    }
  }, [selectedFile]);

  // Handle file retry
  const handleFileRetry = useCallback((fileId: string) => {
    setUploadedFiles(prev => 
      prev.map(file => 
        file.id === fileId 
          ? { ...file, status: 'uploading' as const, progress: 0, error: undefined }
          : file
      )
    );

    // Simulate retry processing
    setTimeout(() => {
      simulateFileProcessing(fileId);
    }, 1000);
  }, [simulateFileProcessing]);

  // Update upload progress
  React.useEffect(() => {
    if (isUploading && Object.keys(uploadProgress).length > 0) {
      setUploadedFiles(prev => 
        prev.map(file => {
          const progress = uploadProgress[file.file.name];
          if (progress !== undefined) {
            return { ...file, progress };
          }
          return file;
        })
      );
    }
  }, [uploadProgress, isUploading]);

  // Calculate upload statistics
  const uploadStats = useMemo(() => {
    const total = uploadedFiles.length;
    const uploading = uploadedFiles.filter(f => f.status === 'uploading').length;
    const processing = uploadedFiles.filter(f => f.status === 'processing').length;
    const completed = uploadedFiles.filter(f => f.status === 'completed').length;
    const error = uploadedFiles.filter(f => f.status === 'error').length;
    const totalSize = uploadedFiles.reduce((sum, f) => sum + f.file.size, 0);

    return { total, uploading, processing, completed, error, totalSize };
  }, [uploadedFiles]);

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-800">File Upload Manager</h2>
          
          <div className="flex items-center space-x-4">
            {/* View Mode Toggle */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setViewMode('grid')}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  viewMode === 'grid'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                🖼️ Grid
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  viewMode === 'list'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                📋 List
              </button>
            </div>

            {/* Stats Toggle */}
            <button
              onClick={() => setShowUploadStats(!showUploadStats)}
              className="px-3 py-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors text-sm"
            >
              📊 Stats
            </button>
          </div>
        </div>

        {/* Upload Statistics */}
        {showUploadStats && (
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4 p-4 bg-gray-50 rounded-lg">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{uploadStats.total}</div>
              <div className="text-sm text-gray-600">Total Files</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-500">{uploadStats.uploading}</div>
              <div className="text-sm text-gray-600">Uploading</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-500">{uploadStats.processing}</div>
              <div className="text-sm text-gray-600">Processing</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-500">{uploadStats.completed}</div>
              <div className="text-sm text-gray-600">Completed</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-500">{uploadStats.error}</div>
              <div className="text-sm text-gray-600">Errors</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-500">{formatFileSize(uploadStats.totalSize)}</div>
              <div className="text-sm text-gray-600">Total Size</div>
            </div>
          </div>
        )}
      </div>

      {/* Upload Area */}
      {showUploadArea && (
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Upload Files</h3>
          <EnhancedFileUpload
            onUploadComplete={handleUploadComplete}
            onUploadError={handleUploadError}
            maxFiles={maxFiles}
            maxFileSize={maxFileSize}
            acceptedTypes={acceptedTypes}
          />
        </div>
      )}

      {/* Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Media Gallery/List */}
        <div className="lg:col-span-2">
          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              Media Files ({uploadedFiles.length})
            </h3>
            
            {uploadedFiles.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-6xl mb-4">📁</div>
                <h4 className="text-lg font-semibold text-gray-700 mb-2">No Files Yet</h4>
                <p className="text-gray-500">Upload some video files to get started</p>
              </div>
            ) : (
              <MediaGallery
                items={uploadedFiles}
                onItemClick={handleFileSelect}
                onItemDelete={handleFileDelete}
                onItemRetry={handleFileRetry}
                layout={viewMode}
                showFilters={true}
                showSearch={true}
                maxItemsPerPage={viewMode === 'grid' ? 8 : 10}
              />
            )}
          </div>
        </div>

        {/* Selected File Preview */}
        <div className="lg:col-span-1">
          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">File Preview</h3>
            
            {selectedFile ? (
              <div className="space-y-4">
                <VideoPreview
                  file={selectedFile.file}
                  showMetadata={true}
                  showControls={true}
                  className="w-full"
                />
                
                <div className="space-y-2">
                  <h4 className="font-medium text-gray-800">File Details</h4>
                  <div className="text-sm text-gray-600 space-y-1">
                    <p><strong>Status:</strong> {selectedFile.status}</p>
                    <p><strong>Uploaded:</strong> {selectedFile.uploadedAt.toLocaleString()}</p>
                    {selectedFile.metadata && (
                      <>
                        <p><strong>Duration:</strong> {Math.floor(selectedFile.metadata.duration / 60)}:{(selectedFile.metadata.duration % 60).toString().padStart(2, '0')}</p>
                        <p><strong>Resolution:</strong> {selectedFile.metadata.width} × {selectedFile.metadata.height}</p>
                      </>
                    )}
                    {selectedFile.error && (
                      <p className="text-red-600"><strong>Error:</strong> {selectedFile.error}</p>
                    )}
                  </div>
                </div>

                <div className="flex space-x-2">
                  <button
                    onClick={() => handleFileRetry(selectedFile.id)}
                    disabled={selectedFile.status !== 'error'}
                    className="flex-1 px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Retry
                  </button>
                  <button
                    onClick={() => handleFileDelete(selectedFile.id)}
                    className="flex-1 px-3 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-gray-500">
                <div className="text-4xl mb-2">👆</div>
                <p>Select a file from the gallery to preview</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Upload Progress Overlay */}
      {isUploading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="text-center">
              <ProgressSpinner size="lg" />
              <h3 className="text-lg font-semibold text-gray-800 mt-4 mb-2">Uploading Files</h3>
              <p className="text-gray-600 mb-4">Please wait while your files are being uploaded...</p>
              
              {/* Progress bars for individual files */}
              <div className="space-y-3">
                {Object.entries(uploadProgress).map(([fileName, progress]) => (
                  <div key={fileName} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600 truncate">{fileName}</span>
                      <span className="text-gray-500">{progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUploadManager;
