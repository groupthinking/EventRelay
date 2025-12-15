# 🚀 Layout Components - Quick Start Guide

## 📦 **Installation**

The layout components are already installed and ready to use. No additional setup required!

## 🎯 **Quick Start**

### **1. Basic Layout Usage**

```tsx
import { DashboardLayout, PageHeader } from './components/layout';

function Dashboard() {
  return (
    <DashboardLayout>
      <PageHeader
        title="Dashboard"
        subtitle="Your video processing dashboard"
      />
      {/* Your content here */}
    </DashboardLayout>
  );
}
```

### **2. Available Layouts**

| Layout | Use Case | Features |
|--------|----------|----------|
| `MainLayout` | Standard pages | Header + Sidebar |
| `DashboardLayout` | Dashboard pages | Centered content, sidebar |
| `ContentLayout` | Content-heavy pages | Optimized reading width |
| `FullWidthLayout` | Immersive content | No sidebar, full width |
| `CenteredLayout` | Forms, landing pages | Centered, focused content |
| `VideoProcessingLayout` | Video workflows | Specialized grid layout |
| `AnalyticsLayout` | Data visualization | Analytics-optimized |

### **3. Navigation Components**

```tsx
import { Header, Sidebar, Breadcrumbs, PageHeader } from './components/layout';

// Header with search and notifications
<Header onMenuToggle={toggleSidebar} />

// Sidebar with navigation
<Sidebar isOpen={sidebarOpen} onClose={closeSidebar} />

// Breadcrumbs for navigation
<Breadcrumbs items={breadcrumbItems} />

// Page header with actions
<PageHeader
  title="Page Title"
  subtitle="Page description"
  actions={<Button>Action</Button>}
/>
```

## 🎨 **Customization**

### **Layout Configuration**

```tsx
<MainLayout 
  showSidebar={false}        // Hide sidebar
  sidebarWidth={320}         // Custom sidebar width
  headerHeight={80}          // Custom header height
  className="custom-class"   // Additional CSS classes
>
  {/* Content */}
</MainLayout>
```

### **Theme Support**

The layout system automatically supports light/dark themes:

```tsx
import { useTheme } from './components/hooks/useTheme';

function App() {
  const { theme, toggleTheme } = useTheme();
  
  return (
    <div className={`theme-${theme}`}>
      {/* Your app with theme support */}
    </div>
  );
}
```

## 📱 **Responsive Behavior**

- **Mobile (< 1024px)**: Sidebar becomes overlay, header adapts
- **Desktop (≥ 1024px)**: Sidebar is persistent, full header features
- **Touch-friendly**: Optimized for mobile devices
- **Auto-adapting**: Layouts automatically adjust to screen size

## 🔧 **Advanced Usage**

### **Custom Sidebar Content**

```tsx
<MainLayout>
  <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
    <div className="lg:col-span-3">
      {/* Main content */}
    </div>
    <div className="lg:col-span-1">
      {/* Custom sidebar content */}
    </div>
  </div>
</MainLayout>
```

### **Breadcrumb Integration**

```tsx
const breadcrumbItems = [
  { label: 'Home', href: '/' },
  { label: 'Videos', href: '/videos' },
  { label: 'AI Tutorials', href: '/videos/ai-tutorials' }
];

<PageHeader
  title="AI Tutorials"
  subtitle="Learn AI from YouTube videos"
  breadcrumbs={breadcrumbItems}
/>
```

## 🧪 **Testing**

### **Test Components Available**

- `LayoutTestSimple` - Basic functionality testing
- `LayoutIntegrationDemo` - Full integration testing
- `LayoutDemo` - Comprehensive feature demonstration

### **Running Tests**

```bash
# Build to check for errors
npm run build

# Start development server
npm start
```

## 📚 **Documentation**

- **Full Documentation**: `README.md`
- **Completion Report**: `PHASE_6_COMPLETION_REPORT.md`
- **Component APIs**: Check individual component files
- **Examples**: See test components for usage patterns

## 🚨 **Troubleshooting**

### **Common Issues**

1. **Build Errors**: Run `npm run build` to check for issues
2. **Missing Components**: Ensure all UI components are installed
3. **Type Errors**: Check TypeScript interfaces in component files
4. **Styling Issues**: Verify Tailwind CSS is properly configured

### **Getting Help**

- Check the component source files for implementation details
- Review the test components for working examples
- Ensure all dependencies are properly installed

---

## 🎉 **You're Ready!**

The layout system is production-ready and provides everything you need to build professional web applications. Start with the basic examples above and customize as needed!

**Happy Coding! 🚀**
