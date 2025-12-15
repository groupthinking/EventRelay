import React, { useState } from 'react';
import FileUploadManager from './FileUploadManager';
import EnhancedFileUpload from './EnhancedFileUpload';
import VideoPreview from './VideoPreview';
import MediaGallery from './MediaGallery';

const FileUploadDemo: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [demoFiles, setDemoFiles] = useState<File[]>([]);
  const [activeTab, setActiveTab] = useState<'manager' | 'upload' | 'preview' | 'gallery'>('manager');

  // Generate demo files for testing
  const generateDemoFiles = () => {
    const demoFileNames = [
      'sample-video-1.mp4',
      'tutorial-video.mov',
      'presentation.avi',
      'demo-content.mkv',
      'test-video.webm'
    ];

    const demoFiles = demoFileNames.map((name, index) => {
      // Create a mock file object
      const file = new File([''], name, {
        type: 'video/mp4',
        lastModified: Date.now() - index * 86400000 // Different dates
      });

      // Mock file size
      Object.defineProperty(file, 'size', {
        value: Math.floor(Math.random() * 100000000) + 10000000 // 10MB - 110MB
      });

      return file;
    });

    setDemoFiles(demoFiles);
  };

  // Handle file selection for preview
  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
  };

  // Handle upload completion
  const handleUploadComplete = (files: File[] | any[]) => {
    console.log('Files uploaded:', files);
    // You could show a success message here
  };

  const tabs = [
    { id: 'manager', label: '📁 File Upload Manager', icon: '📁' },
    { id: 'upload', label: '⬆️ Enhanced Upload', icon: '⬆️' },
    { id: 'preview', label: '🎥 Video Preview', icon: '🎥' },
    { id: 'gallery', label: '🖼️ Media Gallery', icon: '🖼️' }
  ] as const;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-4">
            🎬 File Upload & Media Components Demo
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Explore our comprehensive file upload and media management components with drag & drop, 
            video preview, progress tracking, and more.
          </p>
        </div>

        {/* Navigation Tabs */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-6">
          <div className="flex flex-wrap border-b border-gray-200">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-6 py-4 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="space-y-6">
          {/* File Upload Manager Tab */}
          {activeTab === 'manager' && (
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-blue-800 mb-2">🚀 Complete File Upload Manager</h3>
                <p className="text-blue-700">
                  This comprehensive component combines file upload, video preview, media gallery, and file management 
                  in one powerful interface. Features include drag & drop, progress tracking, file processing simulation, 
                  and detailed statistics.
                </p>
              </div>
              
              <FileUploadManager
                onFilesProcessed={handleUploadComplete}
                maxFiles={20}
                maxFileSize={1000} // 1GB
                acceptedTypes={['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv']}
                showGallery={true}
                showUploadArea={true}
                autoProcess={true}
              />
            </div>
          )}

          {/* Enhanced Upload Tab */}
          {activeTab === 'upload' && (
            <div className="space-y-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-green-800 mb-2">⬆️ Enhanced File Upload Component</h3>
                <p className="text-green-700">
                  Advanced file upload with drag & drop, multiple file support, progress tracking, and comprehensive 
                  error handling. Supports various video formats with configurable limits.
                </p>
              </div>
              
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Upload Configuration</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <h4 className="font-medium text-gray-800">Max Files</h4>
                    <p className="text-2xl font-bold text-blue-600">10</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <h4 className="font-medium text-gray-800">Max File Size</h4>
                    <p className="text-2xl font-bold text-green-600">100 MB</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <h4 className="font-medium text-gray-800">Formats</h4>
                    <p className="text-sm text-gray-600">MP4, MOV, AVI, MKV, WebM</p>
                  </div>
                </div>
                
                <EnhancedFileUpload
                  onUploadComplete={handleUploadComplete}
                  onUploadError={(error) => console.error('Upload error:', error)}
                  maxFiles={10}
                  maxFileSize={100}
                  acceptedTypes={['.mp4', '.mov', '.avi', '.mkv', '.webm']}
                />
              </div>
            </div>
          )}

          {/* Video Preview Tab */}
          {activeTab === 'preview' && (
            <div className="space-y-4">
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-purple-800 mb-2">🎥 Video Preview Component</h3>
                <p className="text-purple-700">
                  Interactive video player with custom controls, metadata display, thumbnail generation, and 
                  comprehensive file information. Supports various video formats with responsive design.
                </p>
              </div>
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* File Selection */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">Select a Video File</h3>
                  
                  {demoFiles.length === 0 ? (
                    <div className="text-center py-8">
                      <button
                        onClick={generateDemoFiles}
                        className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                      >
                        Generate Demo Files
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {demoFiles.map((file, index) => (
                        <button
                          key={index}
                          onClick={() => handleFileSelect(file)}
                          className={`w-full p-3 text-left rounded-lg border transition-colors ${
                            selectedFile === file
                              ? 'border-blue-500 bg-blue-50'
                              : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                          }`}
                        >
                          <div className="flex items-center space-x-3">
                            <span className="text-2xl">🎥</span>
                            <div className="flex-1">
                              <p className="font-medium text-gray-800">{file.name}</p>
                              <p className="text-sm text-gray-500">
                                {(file.size / (1024 * 1024)).toFixed(1)} MB
                              </p>
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Video Preview */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">Video Preview</h3>
                  
                  {selectedFile ? (
                    <VideoPreview
                      file={selectedFile}
                      showMetadata={true}
                      showControls={true}
                      autoPlay={false}
                      muted={true}
                      className="w-full"
                    />
                  ) : (
                    <div className="text-center py-12 text-gray-500">
                      <div className="text-6xl mb-4">👆</div>
                      <p>Select a file from the left to preview</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Media Gallery Tab */}
          {activeTab === 'gallery' && (
            <div className="space-y-4">
              <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-orange-800 mb-2">🖼️ Media Gallery Component</h3>
                <p className="text-orange-700">
                  Advanced media gallery with grid/list views, filtering, search, sorting, and pagination. 
                  Supports various file statuses and provides comprehensive file management capabilities.
                </p>
              </div>
              
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Demo Media Gallery</h3>
                
                {demoFiles.length === 0 ? (
                  <div className="text-center py-8">
                    <button
                      onClick={generateDemoFiles}
                      className="px-6 py-3 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors"
                    >
                      Generate Demo Files for Gallery
                    </button>
                  </div>
                ) : (
                  <MediaGallery
                    items={demoFiles.map((file, index) => ({
                      id: `demo_${index}`,
                      file,
                      uploadedAt: new Date(Date.now() - index * 86400000),
                      status: index === 0 ? 'uploading' : index === 1 ? 'processing' : 'completed',
                      progress: index === 0 ? 75 : undefined,
                      metadata: index > 1 ? {
                        duration: Math.random() * 600 + 60,
                        width: Math.random() > 0.5 ? 1920 : 1280,
                        height: Math.random() > 0.5 ? 1080 : 720,
                        size: file.size
                      } : undefined
                    }))}
                    onItemClick={(item) => handleFileSelect(item.file)}
                    onItemDelete={(itemId) => {
                      setDemoFiles(prev => prev.filter((_, index) => `demo_${index}` !== itemId));
                    }}
                    onItemRetry={(itemId) => {
                      console.log('Retrying item:', itemId);
                    }}
                    layout="grid"
                    showFilters={true}
                    showSearch={true}
                    maxItemsPerPage={8}
                  />
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-12 text-center text-gray-500">
          <p className="text-sm">
            🚀 Built with React, TypeScript, and Tailwind CSS | 
            📚 Comprehensive file upload and media management solution
          </p>
        </div>
      </div>
    </div>
  );
};

export default FileUploadDemo;
