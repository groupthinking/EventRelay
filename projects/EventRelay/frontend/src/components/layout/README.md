# Layout & Navigation Components

This directory contains comprehensive layout and navigation components for building modern, responsive web applications. These components provide a solid foundation for creating consistent user interfaces with proper navigation patterns.

## 🏗️ **Components Overview**

### **Main Layout Components**

#### `MainLayout`
The core layout component that combines header, sidebar, and content area.

```tsx
import { MainLayout } from './Layout';

<MainLayout showSidebar={true} sidebarWidth={256}>
  <div>Your content here</div>
</MainLayout>
```

**Props:**
- `children`: React content to render
- `showSidebar`: Whether to display the sidebar (default: true)
- `sidebarWidth`: Width of the sidebar in pixels (default: 256)
- `headerHeight`: Height of the header in pixels (default: 64)
- `className`: Additional CSS classes

#### **Specialized Layouts**

- **`DashboardLayout`**: Optimized for dashboard pages with centered content
- **`ContentLayout`**: Perfect for content-heavy pages
- **`FullWidthLayout`**: No sidebar for immersive content
- **`CenteredLayout`**: Centered content for optimal readability
- **`VideoProcessingLayout`**: Specialized for video processing workflows
- **`AnalyticsLayout`**: Optimized for data visualization and reporting

### **Header Component**

#### `Header`
A comprehensive header with navigation, search, notifications, and user menu.

```tsx
import { Header } from './Layout';

<Header 
  onMenuToggle={toggleSidebar}
  showSidebar={true}
/>
```

**Features:**
- Responsive design with mobile menu toggle
- Global search functionality
- Notification system with unread counts
- Theme toggle (light/dark mode)
- User profile dropdown menu
- Mobile-optimized search bar

### **Sidebar Component**

#### `Sidebar`
A feature-rich sidebar with hierarchical navigation and quick actions.

```tsx
import { Sidebar } from './Layout';

<Sidebar
  isOpen={sidebarOpen}
  onClose={closeSidebar}
/>
```

**Features:**
- Hierarchical navigation structure
- Collapsible sections
- Search within navigation
- Quick action buttons
- Responsive mobile behavior
- Click-outside-to-close functionality

**Navigation Structure:**
- Dashboard
- Videos (with sub-items: All Videos, Recent, Favorites, Folders)
- Content (Transcripts, Summaries, Insights)
- Analytics (Overview, Performance, Reports)
- Tools (Upload, Processing, Export)
- Team (Members, Permissions, Activity)

### **Breadcrumb Components**

#### `Breadcrumbs`
Flexible breadcrumb navigation with customizable items.

```tsx
import { Breadcrumbs } from './Layout';

<Breadcrumbs
  items={[
    { label: 'Videos', href: '/videos' },
    { label: 'AI Tutorials', href: '/videos/ai-tutorials' },
    { label: 'Introduction to ML', href: '/videos/ai-tutorials/intro-ml' }
  ]}
  showHome={true}
  maxItems={5}
/>
```

#### **Specialized Breadcrumbs**

- **`AutoBreadcrumbs`**: Automatically generates breadcrumbs from pathname
- **`VideoBreadcrumbs`**: For video-related pages
- **`ContentBreadcrumbs`**: For content management pages
- **`AnalyticsBreadcrumbs`**: For analytics and reporting pages

### **Page Header Components**

#### `PageHeader`
Comprehensive page headers with actions, search, filters, and statistics.

```tsx
import { PageHeader } from './Layout';

<PageHeader
  title="Video Management"
  subtitle="Upload, organize, and manage your video content"
  breadcrumbs={breadcrumbItems}
  actions={<CommonActions.Upload />}
  search={{
    placeholder: "Search videos...",
    onSearch: (query) => handleSearch(query)
  }}
  filters={filterOptions}
  stats={statistics}
/>
```

#### **Specialized Page Headers**

- **`VideoPageHeader`**: For video management pages
- **`ContentPageHeader`**: For content management pages
- **`AnalyticsPageHeader`**: For analytics and reporting pages

#### **Common Actions**

Pre-built action buttons for common operations:

```tsx
import { CommonActions } from './Layout';

<CommonActions.Upload onClick={handleUpload} />
<CommonActions.Download onClick={handleDownload} />
<CommonActions.Share onClick={handleShare} />
<CommonActions.Refresh onClick={handleRefresh} loading={isLoading} />
<CommonActions.Settings onClick={handleSettings} />
<CommonActions.More>
  <CommonActions.Download />
  <CommonActions.Share />
</CommonActions.More>
```

## 🎨 **Design Features**

### **Responsive Design**
- Mobile-first approach
- Adaptive layouts for different screen sizes
- Touch-friendly interactions
- Collapsible sidebar on mobile

### **Accessibility**
- Proper ARIA labels
- Keyboard navigation support
- Screen reader compatibility
- Focus management

### **Theme Support**
- Light and dark mode support
- CSS custom properties for theming
- Consistent color schemes
- Smooth transitions

### **Performance**
- Optimized rendering
- Lazy loading support
- Efficient state management
- Minimal re-renders

## 🚀 **Usage Examples**

### **Basic Application Layout**

```tsx
import { MainLayout } from './Layout';

function App() {
  return (
    <MainLayout>
      <div className="p-6">
        <h1>Welcome to UVAI Studio</h1>
        <p>Your video processing dashboard</p>
      </div>
    </MainLayout>
  );
}
```

### **Dashboard with Custom Sidebar**

```tsx
import { DashboardLayout, Sidebar } from './Layout';

function Dashboard() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <DashboardLayout>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <h2>Dashboard Content</h2>
        </div>
        <div className="lg:col-span-1">
          <Sidebar
            isOpen={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
          />
        </div>
      </div>
    </DashboardLayout>
  );
}
```

### **Page with Breadcrumbs and Actions**

```tsx
import { 
  ContentLayout, 
  ContentPageHeader, 
  CommonActions 
} from './Layout';

function VideosPage() {
  return (
    <ContentLayout>
      <ContentPageHeader
        title="Video Library"
        subtitle="Manage your video collection"
        contentType="videos"
        contentCount={156}
        actions={
          <div className="flex gap-2">
            <CommonActions.Upload />
            <CommonActions.CreateFolder />
          </div>
        }
        search={{
          placeholder: "Search videos...",
          onSearch: handleSearch
        }}
      />
      
      {/* Page content */}
    </ContentLayout>
  );
}
```

### **Custom Layout with Breadcrumbs**

```tsx
import { 
  MainLayout, 
  Breadcrumbs, 
  PageHeader 
} from './Layout';

function CustomPage() {
  const breadcrumbs = [
    { label: 'Home', href: '/' },
    { label: 'Projects', href: '/projects' },
    { label: 'Current Project', href: '/projects/current' }
  ];

  return (
    <MainLayout showSidebar={false}>
      <PageHeader
        title="Project Details"
        subtitle="Manage your current project"
        breadcrumbs={breadcrumbs}
        actions={<CommonActions.Settings />}
      />
      
      {/* Page content */}
    </MainLayout>
  );
}
```

## 🔧 **Customization**

### **Styling**
All components use Tailwind CSS classes and can be customized through:
- CSS custom properties
- Tailwind configuration
- Component props
- CSS modules

### **Theming**
Components support both light and dark themes:
- Automatic theme detection
- Manual theme switching
- Consistent color schemes
- Smooth transitions

### **Layout Variations**
Create custom layouts by extending the base components:
- Custom sidebar widths
- Different header heights
- Flexible content areas
- Responsive breakpoints

## 📱 **Mobile Considerations**

### **Responsive Behavior**
- Sidebar collapses on mobile
- Header adapts to small screens
- Touch-friendly interactions
- Optimized spacing and sizing

### **Mobile Navigation**
- Hamburger menu for sidebar
- Overlay navigation
- Swipe gestures support
- Mobile-first design patterns

## 🧪 **Testing**

### **Component Testing**
Each component includes:
- TypeScript interfaces
- PropTypes validation
- Accessibility testing
- Responsive testing

### **Demo Components**
Interactive demos showcase:
- All layout variations
- Component interactions
- Responsive behavior
- Feature demonstrations

## 📚 **Dependencies**

### **Required Packages**
- React 18+
- TypeScript 4.5+
- Tailwind CSS 3.0+
- Lucide React (for icons)
- Next.js 13+ (for routing)

### **Optional Dependencies**
- Framer Motion (for animations)
- React Hook Form (for forms)
- React Query (for data fetching)

## 🚀 **Getting Started**

1. **Install Dependencies**
   ```bash
   npm install lucide-react
   ```

2. **Import Components**
   ```tsx
   import { MainLayout, Header, Sidebar } from './components/Layout';
   ```

3. **Use in Your App**
   ```tsx
   function App() {
     return (
       <MainLayout>
         <div>Your content here</div>
       </MainLayout>
     );
   }
   ```

4. **Customize as Needed**
   - Adjust sidebar width
   - Modify navigation items
   - Customize themes
   - Add custom actions

## 🤝 **Contributing**

When contributing to these components:

1. **Follow the existing patterns**
2. **Add TypeScript types**
3. **Include accessibility features**
4. **Test responsive behavior**
5. **Update documentation**
6. **Add examples and demos**

## 📄 **License**

These components are part of the UVAI Studio project and follow the same licensing terms.

---

**Built with ❤️ for the UVAI Studio project**
