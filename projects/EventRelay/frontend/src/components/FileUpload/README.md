# 🎬 File Upload & Media Components

A comprehensive collection of React components for handling file uploads, video previews, and media management with TypeScript support and modern UI design.

## 🚀 Components Overview

### 1. **FileUploadManager** - Complete Solution
The main component that combines all functionality in one powerful interface.

**Features:**
- 📁 Complete file upload workflow
- 🎥 Video preview and metadata
- 🖼️ Media gallery with grid/list views
- 📊 Upload statistics and progress tracking
- ⚙️ File processing simulation
- 🔄 Retry and error handling

**Usage:**
```tsx
import { FileUploadManager } from '../components/ui';

<FileUploadManager
  onFilesProcessed={(files) => console.log('Files processed:', files)}
  onFileSelected={(file) => console.log('File selected:', file)}
  maxFiles={20}
  maxFileSize={1000} // 1GB
  acceptedTypes={['.mp4', '.mov', '.avi', '.mkv', '.webm']}
  showGallery={true}
  showUploadArea={true}
  autoProcess={true}
/>
```

### 2. **EnhancedFileUpload** - Advanced Upload
Enhanced file upload component with drag & drop and progress tracking.

**Features:**
- 🖱️ Drag & drop support
- 📁 Multiple file selection
- 📊 Real-time progress tracking
- ✅ File validation and error handling
- 🎯 Configurable limits and types
- 🚫 Abort and retry functionality

**Usage:**
```tsx
import { EnhancedFileUpload } from '../components/ui';

<EnhancedFileUpload
  onUploadComplete={(files) => console.log('Upload complete:', files)}
  onUploadError={(error) => console.error('Upload error:', error)}
  maxFiles={10}
  maxFileSize={100} // 100MB
  acceptedTypes={['.mp4', '.mov', '.avi', '.mkv', '.webm']}
/>
```

### 3. **VideoPreview** - Video Player
Interactive video player with custom controls and metadata display.

**Features:**
- 🎮 Custom video controls
- 📊 Metadata extraction and display
- 🖼️ Automatic thumbnail generation
- 📱 Responsive design
- ⏯️ Play/pause, seek, volume control
- 📏 Duration and resolution display

**Usage:**
```tsx
import { VideoPreview } from '../components/ui';

<VideoPreview
  file={videoFile}
  showMetadata={true}
  showControls={true}
  autoPlay={false}
  muted={true}
  loop={false}
  onVideoLoad={(duration, dimensions) => console.log('Video loaded:', { duration, dimensions })}
  onError={(error) => console.error('Video error:', error)}
/>
```

### 4. **MediaGallery** - File Management
Advanced media gallery with filtering, search, and pagination.

**Features:**
- 🖼️ Grid and list view modes
- 🔍 Search and filtering
- 📊 Sorting by name, date, size, duration
- 📄 Pagination support
- 🏷️ Status badges and progress indicators
- 🗑️ File management actions

**Usage:**
```tsx
import { MediaGallery } from '../components/ui';

<MediaGallery
  items={mediaItems}
  onItemClick={(item) => console.log('Item clicked:', item)}
  onItemDelete={(itemId) => console.log('Delete item:', itemId)}
  onItemRetry={(itemId) => console.log('Retry item:', itemId)}
  layout="grid" // or "list"
  showFilters={true}
  showSearch={true}
  maxItemsPerPage={12}
/>
```

## 🎯 Key Features

### **File Upload Capabilities**
- ✅ Drag & drop interface
- ✅ Multiple file selection
- ✅ Progress tracking per file
- ✅ File validation (type, size)
- ✅ Error handling and retry
- ✅ Chunked uploads
- ✅ Concurrent upload management

### **Video Processing**
- 🎥 Multiple format support (MP4, MOV, AVI, MKV, WebM, FLV, WMV)
- 📊 Metadata extraction
- 🖼️ Thumbnail generation
- ⏱️ Duration and resolution detection
- 🔄 Processing status tracking

### **Media Management**
- 📁 File organization and categorization
- 🔍 Advanced search and filtering
- 📊 Sorting and pagination
- 🏷️ Status tracking (uploading, processing, completed, error)
- 🗑️ File deletion and retry
- 📈 Upload statistics and analytics

### **User Experience**
- 🎨 Modern, responsive design
- ♿ Accessibility features
- 📱 Mobile-friendly interface
- 🎭 Smooth animations and transitions
- 🔔 Real-time updates and notifications
- 📊 Progress visualization

## 🛠️ Technical Implementation

### **Dependencies**
- React 18+ with TypeScript
- Tailwind CSS for styling
- Custom hooks for state management
- File API for browser compatibility

### **Browser Support**
- ✅ Chrome 80+
- ✅ Firefox 75+
- ✅ Safari 13+
- ✅ Edge 80+

### **File Size Limits**
- **Default:** 100MB per file
- **Configurable:** Up to 2GB+ (browser dependent)
- **Chunked uploads:** Automatic for large files

### **Supported Formats**
- **Video:** MP4, MOV, AVI, MKV, WebM, FLV, WMV
- **Image:** JPG, PNG, GIF, WebP
- **Document:** PDF, DOC, DOCX, TXT
- **Custom:** Configurable via props

## 📱 Responsive Design

### **Breakpoints**
- **Mobile:** < 768px - Single column layout
- **Tablet:** 768px - 1024px - Two column layout
- **Desktop:** > 1024px - Three column layout
- **Large:** > 1280px - Four column gallery

### **Mobile Optimizations**
- Touch-friendly controls
- Swipe gestures for navigation
- Optimized file selection
- Responsive video player

## 🔧 Customization

### **Styling**
All components use Tailwind CSS classes and can be customized via:
- `className` prop for additional styles
- CSS custom properties for theming
- Component-specific style overrides

### **Configuration**
Components are highly configurable with props for:
- File limits and types
- UI behavior and appearance
- Callback functions
- Feature toggles

### **Theming**
Support for light/dark themes and custom color schemes:
```tsx
// Custom theme example
const customTheme = {
  primary: 'bg-purple-500',
  secondary: 'bg-gray-100',
  accent: 'text-purple-600'
};
```

## 📊 Performance Features

### **Optimizations**
- 🔄 Lazy loading for large galleries
- 📱 Virtual scrolling for long lists
- 🖼️ Image optimization and compression
- 💾 Memory management for file objects
- ⚡ Debounced search and filtering

### **Memory Management**
- Automatic cleanup of file URLs
- Efficient state updates
- Optimized re-renders
- Garbage collection friendly

## 🧪 Testing

### **Demo Components**
- `FileUploadDemo` - Complete showcase
- Interactive examples for each component
- Mock data generation
- Error simulation

### **Test Coverage**
- Component rendering
- User interactions
- File handling
- Error scenarios
- Responsive behavior

## 🚀 Getting Started

### **1. Installation**
```bash
# Components are included in the project
# No additional installation required
```

### **2. Basic Usage**
```tsx
import { FileUploadManager } from '../components/ui';

function App() {
  return (
    <div className="container mx-auto p-6">
      <FileUploadManager
        onFilesProcessed={(files) => {
          console.log('Files processed:', files);
        }}
      />
    </div>
  );
}
```

### **3. Advanced Configuration**
```tsx
<FileUploadManager
  maxFiles={50}
  maxFileSize={2000} // 2GB
  acceptedTypes={['.mp4', '.mov', '.avi']}
  showGallery={true}
  showUploadArea={true}
  autoProcess={true}
  onFilesProcessed={handleFilesProcessed}
  onFileSelected={handleFileSelected}
/>
```

## 🔮 Future Enhancements

### **Planned Features**
- 🌐 Cloud storage integration
- 🔐 File encryption
- 📹 Video editing capabilities
- 🤖 AI-powered content analysis
- 📱 Progressive Web App support
- 🌍 Internationalization

### **Integration Possibilities**
- AWS S3, Google Cloud Storage
- Video processing services
- Content management systems
- Learning management platforms
- E-commerce platforms

## 📚 API Reference

### **Common Props**
- `className` - Additional CSS classes
- `onUploadComplete` - Upload success callback
- `onUploadError` - Upload error callback
- `maxFiles` - Maximum number of files
- `maxFileSize` - Maximum file size in MB
- `acceptedTypes` - Array of accepted file extensions

### **Event Handlers**
- `onFileSelected` - File selection callback
- `onFilesProcessed` - Processing completion callback
- `onItemClick` - Gallery item click callback
- `onItemDelete` - File deletion callback
- `onItemRetry` - File retry callback

## 🤝 Contributing

### **Development Setup**
1. Clone the repository
2. Install dependencies
3. Run development server
4. Make changes and test
5. Submit pull request

### **Code Standards**
- TypeScript for type safety
- Tailwind CSS for styling
- React hooks for state management
- Accessibility-first design
- Mobile-responsive layouts

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### **Common Issues**
- **File too large:** Check `maxFileSize` prop
- **Format not supported:** Verify `acceptedTypes` array
- **Upload fails:** Check network and server configuration
- **Video not playing:** Ensure browser supports format

### **Getting Help**
- Check the demo components
- Review the API documentation
- Test with different file types
- Verify browser compatibility

---

**Built with ❤️ using React, TypeScript, and Tailwind CSS**
