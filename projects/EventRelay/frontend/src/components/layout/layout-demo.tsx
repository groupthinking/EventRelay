'use client';

import React, { useState } from 'react';
import { MainLayout } from './MainLayout';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { Breadcrumbs, AutoBreadcrumbs, VideoBreadcrumbs, ContentBreadcrumbs, AnalyticsBreadcrumbs } from './Breadcrumbs';
import { 
  PageHeader, 
  VideoPageHeader, 
  ContentPageHeader, 
  AnalyticsPageHeader,
  CommonActions 
} from './PageHeader';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Separator } from '../ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';

export const LayoutDemo: React.FC = () => {
  const [currentView, setCurrentView] = useState<'main' | 'dashboard' | 'content' | 'video' | 'analytics'>('main');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const views = {
    main: 'Main View',
    dashboard: 'Dashboard View',
    content: 'Content View',
    video: 'Video View',
    analytics: 'Analytics View'
  };

  const toggleSidebar = () => setSidebarOpen(!sidebarOpen);

  const closeSidebar = () => setSidebarOpen(false);

  const renderDemoContent = () => {
    switch (currentView) {
      case 'dashboard':
        return <DashboardDemoContent />;
      case 'content':
        return <ContentDemoContent />;
      case 'video':
        return <VideoProcessingDemoContent />;
      case 'analytics':
        return <AnalyticsDemoContent />;
      default:
        return <MainDemoContent />;
    }
  };

  return (
    <MainLayout>
      <div className="space-y-8">
        {/* View Selector */}
        <div className="bg-background border-b p-4 rounded-lg">
          <h1 className="text-2xl font-bold mb-4">Layout & Navigation Components Demo</h1>
          <div className="flex flex-wrap gap-2">
            {Object.entries(views).map(([key, name]) => (
              <Button
                key={key}
                variant={currentView === key ? "default" : "outline"}
                size="sm"
                onClick={() => setCurrentView(key as any)}
                className="capitalize"
              >
                {name}
              </Button>
            ))}
          </div>
        </div>

        {/* Demo Content */}
        {renderDemoContent()}
      </div>
    </MainLayout>
  );
};

const MainDemoContent: React.FC = () => (
  <div className="space-y-8">
    <div>
      <h2 className="text-2xl font-bold mb-4">Main Layout Demo</h2>
      <p className="text-muted-foreground">
        This demonstrates the basic MainLayout component with header, sidebar, and content area.
      </p>
    </div>

    {/* Breadcrumbs Demo */}
    <Card>
      <CardHeader>
        <CardTitle>Breadcrumbs Components</CardTitle>
        <CardDescription>Various breadcrumb navigation patterns</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <h4 className="font-medium mb-2">Basic Breadcrumbs</h4>
          <Breadcrumbs
            items={[
              { label: 'Videos', href: '/videos' },
              { label: 'AI Tutorials', href: '/videos/ai-tutorials' },
              { label: 'Introduction to ML', href: '/videos/ai-tutorials/intro-ml' }
            ]}
          />
        </div>

        <div>
          <h4 className="font-medium mb-2">Auto Breadcrumbs</h4>
          <AutoBreadcrumbs pathname="/videos/ai-tutorials/intro-ml" />
        </div>

        <div>
          <h4 className="font-medium mb-2">Specialized Breadcrumbs</h4>
          <div className="space-y-2">
            <VideoBreadcrumbs 
              videoTitle="Introduction to Machine Learning" 
              folderName="AI Tutorials" 
            />
            <ContentBreadcrumbs 
              contentType="transcripts" 
              contentTitle="ML Transcript" 
            />
            <AnalyticsBreadcrumbs 
              reportType="performance" 
              reportName="Q4 Performance Report" 
            />
          </div>
        </div>
      </CardContent>
    </Card>

    {/* Page Headers Demo */}
    <Card>
      <CardHeader>
        <CardTitle>Page Header Components</CardTitle>
        <CardDescription>Different page header patterns with actions and metadata</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div>
          <h4 className="font-medium mb-2">Basic Page Header</h4>
          <PageHeader
            title="Video Management"
            subtitle="Upload, organize, and manage your video content"
            breadcrumbs={[
              { label: 'Dashboard', href: '/dashboard' },
              { label: 'Videos', href: '/videos' }
            ]}
            actions={
              <div className="flex gap-2">
                <CommonActions.Upload />
                <CommonActions.Settings />
              </div>
            }
            search={{
              placeholder: "Search videos...",
              onSearch: (query) => console.log('Search:', query)
            }}
            filters={[
              {
                label: 'Status',
                options: [
                  { value: 'processing', label: 'Processing' },
                  { value: 'completed', label: 'Completed' },
                  { value: 'failed', label: 'Failed' }
                ]
              }
            ]}
            stats={[
              { label: 'Total Videos', value: 156, change: { value: 12, isPositive: true } },
              { label: 'Processing', value: 8, change: { value: 3, isPositive: false } },
              { label: 'Completed', value: 148, change: { value: 15, isPositive: true } }
            ]}
          />
        </div>

        <Separator />

        <div>
          <h4 className="font-medium mb-2">Video Page Header</h4>
          <VideoPageHeader
            title="AI Tutorials"
            subtitle="Educational content about artificial intelligence and machine learning"
            folderName="Tutorials"
            videoCount={24}
            actions={
              <div className="flex gap-2">
                <CommonActions.Upload />
                <CommonActions.Share />
              </div>
            }
            search={{
              placeholder: "Search in AI Tutorials...",
              onSearch: (query) => console.log('Search:', query)
            }}
          />
        </div>

        <Separator />

        <div>
          <h4 className="font-medium mb-2">Content Page Header</h4>
          <ContentPageHeader
            title="Video Transcripts"
            subtitle="AI-generated transcripts from your video content"
            contentType="transcripts"
            contentCount={89}
            actions={
              <div className="flex gap-2">
                <CommonActions.Download />
                <CommonActions.Refresh />
              </div>
            }
          />
        </div>

        <Separator />

        <div>
          <h4 className="font-medium mb-2">Analytics Page Header</h4>
          <AnalyticsPageHeader
            title="Performance Overview"
            subtitle="Track your video performance and engagement metrics"
            reportType="overview"
            actions={
              <div className="flex gap-2">
                <CommonActions.Settings />
                <CommonActions.More>
                  <CommonActions.Download />
                  <CommonActions.Share />
                </CommonActions.More>
              </div>
            }
            filters={[
              {
                label: 'Time Range',
                options: [
                  { value: '7d', label: 'Last 7 days' },
                  { value: '30d', label: 'Last 30 days' },
                  { value: '90d', label: 'Last 90 days' }
                ]
              }
            ]}
          />
        </div>
      </CardContent>
    </Card>
  </div>
);

const DashboardDemoContent: React.FC = () => (
  <div className="space-y-6">
    <div>
      <h2 className="text-2xl font-bold mb-4">Dashboard Layout Demo</h2>
      <p className="text-muted-foreground">
        This demonstrates the DashboardLayout with centered content and sidebar navigation.
      </p>
    </div>

    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Recent Videos</CardTitle>
          <CardDescription>Your latest video uploads</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {['AI Basics', 'ML Fundamentals', 'Deep Learning Intro'].map((title, i) => (
              <div key={i} className="flex items-center justify-between">
                <span className="text-sm">{title}</span>
                <Badge variant="secondary">2h ago</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Processing Status</CardTitle>
          <CardDescription>Current video processing</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm">Neural Networks</span>
              <Badge variant="default">Processing</Badge>
            </div>
            <div className="w-full bg-muted rounded-full h-2">
              <div className="bg-primary h-2 rounded-full" style={{ width: '65%' }}></div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>Common tasks</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Button size="sm" className="w-full">Upload Video</Button>
            <Button size="sm" variant="outline" className="w-full">Create Folder</Button>
            <Button size="sm" variant="outline" className="w-full">Generate Report</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
);

const ContentDemoContent: React.FC = () => (
  <div className="space-y-6">
    <div>
      <h2 className="text-2xl font-bold mb-4">Content Layout Demo</h2>
      <p className="text-muted-foreground">
        This demonstrates the ContentLayout optimized for content-heavy pages.
      </p>
    </div>

    <Card>
      <CardHeader>
        <CardTitle>Content Management</CardTitle>
        <CardDescription>Organize and manage your video content</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <h4 className="font-medium">Video Transcripts</h4>
              <p className="text-sm text-muted-foreground">89 transcripts available</p>
            </div>
            <Button variant="outline">View All</Button>
          </div>
          
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <h4 className="font-medium">AI Summaries</h4>
              <p className="text-sm text-muted-foreground">67 summaries generated</p>
            </div>
            <Button variant="outline">View All</Button>
          </div>
          
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <h4 className="font-medium">Content Insights</h4>
              <p className="text-sm text-muted-foreground">23 insights available</p>
            </div>
            <Button variant="outline">View All</Button>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
);

const VideoProcessingDemoContent: React.FC = () => (
  <div className="space-y-6">
    <div>
      <h2 className="text-2xl font-bold mb-4">Video Processing Layout Demo</h2>
      <p className="text-muted-foreground">
        This demonstrates the VideoProcessingLayout with a specialized sidebar for processing controls.
      </p>
    </div>

    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2">
        <Card>
          <CardHeader>
            <CardTitle>Video Processing Queue</CardTitle>
            <CardDescription>Manage your video processing tasks</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[
                { name: 'AI Tutorial Part 1', status: 'Processing', progress: 75 },
                { name: 'ML Fundamentals', status: 'Queued', progress: 0 },
                { name: 'Deep Learning Basics', status: 'Completed', progress: 100 }
              ].map((video, i) => (
                <div key={i} className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{video.name}</span>
                    <Badge variant={video.status === 'Completed' ? 'default' : 'secondary'}>
                      {video.status}
                    </Badge>
                  </div>
                  <div className="w-full bg-muted rounded-full h-2">
                    <div 
                      className="bg-primary h-2 rounded-full transition-all duration-300" 
                      style={{ width: `${video.progress}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="lg:col-span-1">
        <Card>
          <CardHeader>
            <CardTitle>Processing Controls</CardTitle>
            <CardDescription>Manage processing settings</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium">Quality</label>
                <select className="w-full mt-1 p-2 border rounded-md">
                  <option>High</option>
                  <option>Medium</option>
                  <option>Low</option>
                </select>
              </div>
              
              <div>
                <label className="text-sm font-medium">Language</label>
                <select className="w-full mt-1 p-2 border rounded-md">
                  <option>English</option>
                  <option>Spanish</option>
                  <option>French</option>
                </select>
              </div>
              
              <Button className="w-full">Start Processing</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
);

const AnalyticsDemoContent: React.FC = () => (
  <div className="space-y-6">
    <div>
      <h2 className="text-2xl font-bold mb-4">Analytics Layout Demo</h2>
      <p className="text-muted-foreground">
        This demonstrates the AnalyticsLayout optimized for data visualization and reporting.
      </p>
    </div>

    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Total Views</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">12,847</div>
          <p className="text-xs text-muted-foreground">+20.1% from last month</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Watch Time</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">2,847h</div>
          <p className="text-xs text-muted-foreground">+12.5% from last month</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Engagement Rate</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">68.2%</div>
          <p className="text-xs text-muted-foreground">+5.3% from last month</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Subscribers</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">1,247</div>
          <p className="text-xs text-muted-foreground">+8.7% from last month</p>
        </CardContent>
      </Card>
    </div>

    <Card>
      <CardHeader>
        <CardTitle>Performance Trends</CardTitle>
        <CardDescription>Monthly performance metrics</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64 bg-muted rounded-lg flex items-center justify-center">
          <p className="text-muted-foreground">Chart visualization would go here</p>
        </div>
      </CardContent>
    </Card>
  </div>
);

const FullWidthDemoContent: React.FC = () => (
  <div className="space-y-6">
    <div>
      <h2 className="text-2xl font-bold mb-4">Full Width Layout Demo</h2>
      <p className="text-muted-foreground">
        This demonstrates the FullWidthLayout without sidebar for immersive content.
      </p>
    </div>

    <div className="bg-muted/50 rounded-lg p-8 text-center">
      <h3 className="text-xl font-semibold mb-2">Immersive Content Area</h3>
      <p className="text-muted-foreground">
        This layout is perfect for video players, presentations, and full-screen experiences.
      </p>
    </div>

    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Content Section 1</CardTitle>
        </CardHeader>
        <CardContent>
          <p>This section takes advantage of the full width layout.</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Content Section 2</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Another section that benefits from the expanded layout.</p>
        </CardContent>
      </Card>
    </div>
  </div>
);

const CenteredDemoContent: React.FC = () => (
  <div className="space-y-6">
    <div>
      <h2 className="text-2xl font-bold mb-4">Centered Layout Demo</h2>
      <p className="text-muted-foreground">
        This demonstrates the CenteredLayout for focused, readable content.
      </p>
    </div>

    <Card className="max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>Focused Content</CardTitle>
        <CardDescription>This content is centered for optimal readability</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-muted-foreground mb-4">
          The centered layout is perfect for forms, articles, and content that benefits from 
          focused reading. It provides an optimal line length for text content and creates 
          a clean, professional appearance.
        </p>
        
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-primary rounded-full"></div>
            <span>Optimal line length for reading</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-primary rounded-full"></div>
            <span>Clean, focused design</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-primary rounded-full"></div>
            <span>Professional appearance</span>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
);

export default LayoutDemo;
