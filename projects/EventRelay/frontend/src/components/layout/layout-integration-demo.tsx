'use client';

import React, { useState } from 'react';
import { MainLayout } from './MainLayout';
import { PageHeader } from './PageHeader';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Badge } from '../ui/badge';

export const LayoutIntegrationDemo: React.FC = () => {
  const [currentView, setCurrentView] = useState<'dashboard' | 'content' | 'video' | 'analytics'>('dashboard');

  const views = {
    dashboard: { name: 'Dashboard View', description: 'Optimized for dashboard pages' },
    content: { name: 'Content View', description: 'Perfect for content-heavy pages' },
    video: { name: 'Video View', description: 'Specialized for video workflows' },
    analytics: { name: 'Analytics View', description: 'Optimized for data visualization' }
  };

  const renderContent = () => {
    switch (currentView) {
      case 'dashboard':
        return <DashboardContent />;
      case 'content':
        return <ContentContent />;
      case 'video':
        return <VideoContent />;
      case 'analytics':
        return <AnalyticsContent />;
      default:
        return <DashboardContent />;
    }
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title={views[currentView].name}
          subtitle={views[currentView].description}
        />

        {/* View Selector */}
        <Card>
          <CardHeader>
            <CardTitle>View Selector</CardTitle>
            <CardDescription>Choose different view modes to see how the content adapts</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {Object.entries(views).map(([key, view]) => (
                <Button
                  key={key}
                  variant={currentView === key ? "default" : "outline"}
                  size="sm"
                  onClick={() => setCurrentView(key as any)}
                  className="capitalize"
                >
                  {view.name}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Content Area */}
        {renderContent()}
      </div>
    </MainLayout>
  );
};

const DashboardContent: React.FC = () => (
  <div className="space-y-6">
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Total Videos</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">1,234</div>
          <p className="text-xs text-muted-foreground">+12% from last month</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Processing</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">23</div>
          <p className="text-xs text-muted-foreground">Currently in queue</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Completed</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">1,211</div>
          <p className="text-xs text-muted-foreground">98.1% success rate</p>
        </CardContent>
      </Card>
    </div>
    
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
        <CardDescription>Latest video processing activities</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {[
            { title: 'AI Tutorial Video', status: 'completed', time: '2 minutes ago' },
            { title: 'Machine Learning Basics', status: 'processing', time: '15 minutes ago' },
            { title: 'Data Science Intro', status: 'queued', time: '1 hour ago' }
          ].map((item, i) => (
            <div key={i} className="flex items-center justify-between">
              <div>
                <p className="font-medium">{item.title}</p>
                <p className="text-sm text-muted-foreground">{item.time}</p>
              </div>
              <Badge variant={item.status === 'completed' ? 'default' : item.status === 'processing' ? 'secondary' : 'outline'}>
                {item.status}
              </Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  </div>
);

const ContentContent: React.FC = () => (
  <div className="space-y-6">
    <Card>
      <CardHeader>
        <CardTitle>Content Management</CardTitle>
        <CardDescription>Manage your video content and metadata</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs value="videos" onValueChange={() => {}} className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="videos">Videos</TabsTrigger>
            <TabsTrigger value="playlists">Playlists</TabsTrigger>
            <TabsTrigger value="channels">Channels</TabsTrigger>
          </TabsList>
          <TabsContent value="videos" className="space-y-4">
            <p>Video management interface would go here.</p>
            <Button>Add New Video</Button>
          </TabsContent>
          <TabsContent value="playlists" className="space-y-4">
            <p>Playlist management interface would go here.</p>
            <Button>Create Playlist</Button>
          </TabsContent>
          <TabsContent value="channels" className="space-y-4">
            <p>Channel management interface would go here.</p>
            <Button>Manage Channels</Button>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  </div>
);

const VideoContent: React.FC = () => (
  <div className="space-y-6">
    <Card>
      <CardHeader>
        <CardTitle>Video Processing Queue</CardTitle>
        <CardDescription>Monitor and manage video processing tasks</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <p className="font-medium">Introduction to AI</p>
              <p className="text-sm text-muted-foreground">Processing: 65% complete</p>
            </div>
            <div className="w-32 bg-gray-200 rounded-full h-2">
              <div className="bg-blue-600 h-2 rounded-full" style={{ width: '65%' }}></div>
            </div>
          </div>
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <p className="font-medium">Machine Learning Basics</p>
              <p className="text-sm text-muted-foreground">Queued for processing</p>
            </div>
            <Badge variant="outline">Queued</Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
);

const AnalyticsContent: React.FC = () => (
  <div className="space-y-6">
    <Card>
      <CardHeader>
        <CardTitle>Analytics Dashboard</CardTitle>
        <CardDescription>View detailed analytics and insights</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <h4 className="font-semibold">Performance Metrics</h4>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>Processing Speed</span>
                <span className="font-medium">2.3x faster</span>
              </div>
              <div className="flex justify-between">
                <span>Success Rate</span>
                <span className="font-medium">98.1%</span>
              </div>
              <div className="flex justify-between">
                <span>Uptime</span>
                <span className="font-medium">99.9%</span>
              </div>
            </div>
          </div>
          <div className="space-y-4">
            <h4 className="font-semibold">Usage Statistics</h4>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>Videos Processed</span>
                <span className="font-medium">1,234</span>
              </div>
              <div className="flex justify-between">
                <span>Active Users</span>
                <span className="font-medium">156</span>
              </div>
              <div className="flex justify-between">
                <span>API Calls</span>
                <span className="font-medium">45.2K</span>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
);
