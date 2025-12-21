import React, { useState, useCallback, useRef, DragEvent } from 'react';
import { useFileUpload } from '../../hooks/useFileUpload';
import { ProgressBar } from '../ui/progress-bar';
import { ProgressSpinner } from '../ui/progress-spinner';

interface FileUploadProps {
  onUploadComplete?: (files: File[]) => void;
  onUploadError?: (error: string) => void;
  maxFiles?: number;
  maxFileSize?: number; // in MB
  acceptedTypes?: string[];
  className?: string;
}

const EnhancedFileUpload: React.FC<FileUploadProps> = ({
  onUploadComplete,
  onUploadError,
  maxFiles = 10,
  maxFileSize = 100, // 100MB default
  acceptedTypes = ['.mp4', '.mov', '.avi', '.mkv', '.webm'],
  className = ''
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  
  const {
    addFiles,
    uploadProgress,
    isUploading,
    error: uploadError,
    clearAll
  } = useFileUpload();

  const handleFileSelect = useCallback((files: FileList | null) => {
    if (!files) return;

    const fileArray = Array.from(files);
    const validFiles = fileArray.filter(file => {
      // Check file size
      if (file.size > maxFileSize * 1024 * 1024) {
        onUploadError?.(`File ${file.name} is too large. Maximum size is ${maxFileSize}MB`);
        return false;
      }

      // Check file type
      const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
      if (!acceptedTypes.includes(fileExtension)) {
        onUploadError?.(`File ${file.name} is not a supported video format`);
        return false;
      }

      return true;
    });

    if (validFiles.length + selectedFiles.length > maxFiles) {
      onUploadError?.(`Maximum ${maxFiles} files allowed`);
      return;
    }

    setSelectedFiles(prev => [...prev, ...validFiles]);
  }, [selectedFiles, maxFiles, maxFileSize, acceptedTypes, onUploadError]);

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    handleFileSelect(e.dataTransfer.files);
  }, [handleFileSelect]);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    handleFileSelect(e.target.files);
  }, [handleFileSelect]);

  const handleUpload = useCallback(async () => {
    if (selectedFiles.length === 0) return;

    try {
      await addFiles(selectedFiles);
      onUploadComplete?.(selectedFiles);
      setSelectedFiles([]);
      clearAll();
    } catch (error) {
      onUploadError?.(error instanceof Error ? error.message : 'Upload failed');
    }
  }, [selectedFiles, addFiles, onUploadComplete, onUploadError, clearAll]);

  const removeFile = useCallback((index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  const clearAllFiles = useCallback(() => {
    setSelectedFiles([]);
    clearAll();
  }, [clearAll]);

  const openFileDialog = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (fileName: string): string => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'mp4':
      case 'mov':
      case 'avi':
      case 'mkv':
      case 'webm':
        return '🎥';
      default:
        return '📄';
    }
  };

  return (
    <div className={`w-full ${className}`}>
      {/* Drag & Drop Zone */}
      <div
        className={`
          relative border-2 border-dashed rounded-lg p-8 text-center transition-all duration-200
          ${isDragOver 
            ? 'border-blue-500 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
          }
          ${selectedFiles.length > 0 ? 'border-green-500 bg-green-50' : ''}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={acceptedTypes.join(',')}
          onChange={handleFileInputChange}
          className="hidden"
        />

        {selectedFiles.length === 0 ? (
          <div className="space-y-4">
            <div className="text-6xl">📁</div>
            <h3 className="text-lg font-semibold text-gray-700">
              Drop video files here or click to browse
            </h3>
            <p className="text-sm text-gray-500">
              Supports {acceptedTypes.join(', ')} up to {maxFileSize}MB
            </p>
            <button
              onClick={openFileDialog}
              className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              Choose Files
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="text-4xl">✅</div>
            <h3 className="text-lg font-semibold text-gray-700">
              {selectedFiles.length} file(s) selected
            </h3>
            <div className="flex gap-2 justify-center">
              <button
                onClick={openFileDialog}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
              >
                Add More
              </button>
              <button
                onClick={clearAllFiles}
                className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
              >
                Clear All
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Selected Files List */}
      {selectedFiles.length > 0 && (
        <div className="mt-6 space-y-3">
          <h4 className="font-semibold text-gray-700">Selected Files:</h4>
          {selectedFiles.map((file, index) => (
            <div
              key={`${file.name}-${index}`}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
            >
              <div className="flex items-center space-x-3">
                <span className="text-2xl">{getFileIcon(file.name)}</span>
                <div>
                  <p className="font-medium text-gray-800">{file.name}</p>
                  <p className="text-sm text-gray-500">{formatFileSize(file.size)}</p>
                </div>
              </div>
              <button
                onClick={() => removeFile(index)}
                className="text-red-500 hover:text-red-700 transition-colors"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Upload Progress */}
      {isUploading && (
        <div className="mt-6 space-y-3">
          <h4 className="font-semibold text-gray-700">Upload Progress:</h4>
          <div className="space-y-2">
            {Object.entries(uploadProgress).map(([fileName, progress]) => (
              <div key={fileName} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">{fileName}</span>
                  <span className="text-gray-500">{progress}%</span>
                </div>
                <ProgressBar 
                  currentStep={progress} 
                  totalSteps={100}
                  className="h-2"
                  showSteps={false}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload Button */}
      {selectedFiles.length > 0 && !isUploading && (
        <div className="mt-6">
          <button
            onClick={handleUpload}
            className="w-full py-3 bg-green-500 text-white font-semibold rounded-lg hover:bg-green-600 transition-colors disabled:bg-gray-400"
            disabled={selectedFiles.length === 0}
          >
            Upload {selectedFiles.length} File{selectedFiles.length !== 1 ? 's' : ''}
          </button>
        </div>
      )}

      {/* Error Display */}
      {uploadError && (
        <div className="mt-4 p-3 bg-red-100 border border-red-300 rounded-lg">
          <p className="text-red-700 text-sm">{uploadError}</p>
        </div>
      )}

      {/* Loading Overlay */}
      {isUploading && (
        <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center rounded-lg">
          <div className="text-center">
            <ProgressSpinner size="lg" />
            <p className="mt-2 text-gray-600">Uploading files...</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default EnhancedFileUpload;
