import React, { useState, useCallback, useMemo } from 'react';
import VideoPreview from './VideoPreview';
import { ProgressSpinner } from '../ui/progress-spinner';

interface MediaItem {
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

interface MediaGalleryProps {
  items: MediaItem[];
  onItemClick?: (item: MediaItem) => void;
  onItemDelete?: (itemId: string) => void;
  onItemRetry?: (itemId: string) => void;
  className?: string;
  layout?: 'grid' | 'list';
  showFilters?: boolean;
  showSearch?: boolean;
  maxItemsPerPage?: number;
}

const MediaGallery: React.FC<MediaGalleryProps> = ({
  items,
  onItemClick,
  onItemDelete,
  onItemRetry,
  className = '',
  layout = 'grid',
  showFilters = true,
  showSearch = true,
  maxItemsPerPage = 12
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'name' | 'date' | 'size' | 'duration'>('date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [currentPage, setCurrentPage] = useState(1);

  // Filter and sort items
  const filteredAndSortedItems = useMemo(() => {
    let filtered = items.filter(item => {
      // Search filter
      if (searchTerm && !item.file.name.toLowerCase().includes(searchTerm.toLowerCase())) {
        return false;
      }
      
      // Status filter
      if (statusFilter !== 'all' && item.status !== statusFilter) {
        return false;
      }
      
      return true;
    });

    // Sort items
    filtered.sort((a, b) => {
      let aValue: any, bValue: any;
      
      switch (sortBy) {
        case 'name':
          aValue = a.file.name.toLowerCase();
          bValue = b.file.name.toLowerCase();
          break;
        case 'date':
          aValue = a.uploadedAt.getTime();
          bValue = b.uploadedAt.getTime();
          break;
        case 'size':
          aValue = a.file.size;
          bValue = b.file.size;
          break;
        case 'duration':
          aValue = a.metadata?.duration || 0;
          bValue = b.metadata?.duration || 0;
          break;
        default:
          return 0;
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });

    return filtered;
  }, [items, searchTerm, statusFilter, sortBy, sortOrder]);

  // Pagination
  const totalPages = Math.ceil(filteredAndSortedItems.length / maxItemsPerPage);
  const startIndex = (currentPage - 1) * maxItemsPerPage;
  const paginatedItems = filteredAndSortedItems.slice(startIndex, startIndex + maxItemsPerPage);

  // Handle search
  const handleSearch = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
    setCurrentPage(1); // Reset to first page
  }, []);

  // Handle status filter change
  const handleStatusFilterChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setStatusFilter(e.target.value);
    setCurrentPage(1); // Reset to first page
  }, []);

  // Handle sort change
  const handleSortChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setSortBy(e.target.value as any);
    setCurrentPage(1); // Reset to first page
  }, []);

  // Handle sort order toggle
  const handleSortOrderToggle = useCallback(() => {
    setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
  }, []);

  // Handle page change
  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
  }, []);

  // Get status badge
  const getStatusBadge = (status: string) => {
    const statusConfig = {
      uploading: { color: 'bg-blue-100 text-blue-800', text: 'Uploading' },
      processing: { color: 'bg-yellow-100 text-yellow-800', text: 'Processing' },
      completed: { color: 'bg-green-100 text-green-800', text: 'Completed' },
      error: { color: 'bg-red-100 text-red-800', text: 'Error' }
    };

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.uploading;
    
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${config.color}`}>
        {config.text}
      </span>
    );
  };

  // Get status icon
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'uploading':
        return <ProgressSpinner size="sm" />;
      case 'processing':
        return '⚙️';
      case 'completed':
        return '✅';
      case 'error':
        return '❌';
      default:
        return '📁';
    }
  };

  if (items.length === 0) {
    return (
      <div className={`text-center py-12 ${className}`}>
        <div className="text-6xl mb-4">📁</div>
        <h3 className="text-lg font-semibold text-gray-700 mb-2">No Media Files</h3>
        <p className="text-gray-500">Upload some video files to get started</p>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Filters and Search */}
      {(showFilters || showSearch) && (
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
          <div className="flex flex-wrap gap-4 items-center">
            {/* Search */}
            {showSearch && (
              <div className="flex-1 min-w-64">
                <input
                  type="text"
                  placeholder="Search files..."
                  value={searchTerm}
                  onChange={handleSearch}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            )}

            {/* Status Filter */}
            {showFilters && (
              <select
                value={statusFilter}
                onChange={handleStatusFilterChange}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">All Status</option>
                <option value="uploading">Uploading</option>
                <option value="processing">Processing</option>
                <option value="completed">Completed</option>
                <option value="error">Error</option>
              </select>
            )}

            {/* Sort */}
            {showFilters && (
              <div className="flex items-center space-x-2">
                <select
                  value={sortBy}
                  onChange={handleSortChange}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="name">Name</option>
                  <option value="date">Date</option>
                  <option value="size">Size</option>
                  <option value="duration">Duration</option>
                </select>
                <button
                  onClick={handleSortOrderToggle}
                  className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                  title={`Sort ${sortOrder === 'asc' ? 'Descending' : 'Ascending'}`}
                >
                  {sortOrder === 'asc' ? '↑' : '↓'}
                </button>
              </div>
            )}
          </div>

          {/* Results count */}
          <div className="mt-3 text-sm text-gray-600">
            Showing {filteredAndSortedItems.length} of {items.length} files
          </div>
        </div>
      )}

      {/* Media Grid/List */}
      <div className={layout === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6' : 'space-y-4'}>
        {paginatedItems.map((item) => (
          <div
            key={item.id}
            className={`bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow cursor-pointer ${
              layout === 'list' ? 'flex' : ''
            }`}
            onClick={() => onItemClick?.(item)}
          >
            {/* Status Header */}
            <div className="p-3 border-b border-gray-100 bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  {getStatusIcon(item.status)}
                  {getStatusBadge(item.status)}
                </div>
                
                <div className="flex items-center space-x-2">
                  {onItemRetry && item.status === 'error' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onItemRetry(item.id);
                      }}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                      title="Retry"
                    >
                      🔄
                    </button>
                  )}
                  
                  {onItemDelete && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onItemDelete(item.id);
                      }}
                      className="text-red-600 hover:text-red-800 text-sm"
                      title="Delete"
                    >
                      🗑️
                    </button>
                  )}
                </div>
              </div>

              {/* Progress bar for uploading/processing */}
              {item.status === 'uploading' && item.progress !== undefined && (
                <div className="mt-2">
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-600 mt-1">{item.progress}%</div>
                </div>
              )}
            </div>

            {/* Video Preview */}
            <div className={layout === 'list' ? 'flex-1' : ''}>
              <VideoPreview
                file={item.file}
                showMetadata={false}
                showControls={false}
                className="w-full"
              />
            </div>

            {/* Item Info */}
            <div className="p-3">
              <h4 className="font-medium text-gray-800 truncate mb-1" title={item.file.name}>
                {item.file.name}
              </h4>
              
              <div className="text-sm text-gray-600 space-y-1">
                <p>Uploaded: {item.uploadedAt.toLocaleDateString()}</p>
                {item.metadata && (
                  <>
                    <p>Duration: {Math.floor(item.metadata.duration / 60)}:{(item.metadata.duration % 60).toString().padStart(2, '0')}</p>
                    <p>Resolution: {item.metadata.width} × {item.metadata.height}</p>
                  </>
                )}
                {item.error && (
                  <p className="text-red-600 text-xs">{item.error}</p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center items-center space-x-2">
          <button
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage === 1}
            className="px-3 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Previous
          </button>
          
          {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
            <button
              key={page}
              onClick={() => handlePageChange(page)}
              className={`px-3 py-2 border rounded-lg ${
                page === currentPage
                  ? 'bg-blue-500 text-white border-blue-500'
                  : 'border-gray-300 hover:bg-gray-50'
              }`}
            >
              {page}
            </button>
          ))}
          
          <button
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="px-3 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

export default MediaGallery;
