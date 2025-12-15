'use client';

import React from 'react';
import { MainLayout } from './MainLayout';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { Breadcrumbs } from './Breadcrumbs';
import { PageHeader } from './PageHeader';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';

export const LayoutTest: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = React.useState(false);

  const toggleSidebar = () => setSidebarOpen(!sidebarOpen);
  const closeSidebar = () => setSidebarOpen(false);

  const breadcrumbItems = [
    { label: 'Home', href: '/' },
    { label: 'Videos', href: '/videos' },
    { label: 'AI Tutorials', href: '/videos/ai-tutorials' }
  ];

  return (
    <MainLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold mb-4">Layout Components Test</h2>
          <p className="text-muted-foreground">
            This page tests all the layout and navigation components to ensure they work correctly.
          </p>
        </div>

        {/* Header Test */}
        <Card>
          <CardHeader>
            <CardTitle>Header Component Test</CardTitle>
            <CardDescription>Testing the header component functionality</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="border rounded-lg p-4">
              <Header 
                onMenuToggle={toggleSidebar}
                showSidebar={true}
              />
            </div>
          </CardContent>
        </Card>

        {/* Sidebar Test */}
        <Card>
          <CardHeader>
            <CardTitle>Sidebar Component Test</CardTitle>
            <CardDescription>Testing the sidebar component functionality</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="border rounded-lg p-4">
              <Sidebar
                isOpen={sidebarOpen}
                onClose={closeSidebar}
              />
              <div className="mt-4">
                <Button onClick={toggleSidebar}>
                  {sidebarOpen ? 'Close' : 'Open'} Sidebar
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Breadcrumbs Test */}
        <Card>
          <CardHeader>
            <CardTitle>Breadcrumbs Component Test</CardTitle>
            <CardDescription>Testing the breadcrumbs component functionality</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h4 className="font-medium mb-2">Basic Breadcrumbs</h4>
                <Breadcrumbs items={breadcrumbItems} />
              </div>
              
              <div>
                <h4 className="font-medium mb-2">Breadcrumbs with Home</h4>
                <Breadcrumbs items={breadcrumbItems} showHome={true} />
              </div>
              
              <div>
                <h4 className="font-medium mb-2">Limited Breadcrumbs</h4>
                <Breadcrumbs items={breadcrumbItems} maxItems={2} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Page Header Test */}
        <Card>
          <CardHeader>
            <CardTitle>Page Header Component Test</CardTitle>
            <CardDescription>Testing the page header component functionality</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <PageHeader
                title="Test Page"
                subtitle="This is a test page for the layout components"
                breadcrumbs={breadcrumbItems}
                actions={
                  <div className="flex gap-2">
                    <Button>Primary Action</Button>
                    <Button variant="outline">Secondary Action</Button>
                  </div>
                }
                search={{
                  placeholder: "Search test content...",
                  onSearch: (query) => console.log('Search:', query)
                }}
                filters={[
                  {
                    label: 'Category',
                    options: [
                      { value: 'all', label: 'All' },
                      { value: 'videos', label: 'Videos' },
                      { value: 'documents', label: 'Documents' }
                    ]
                  }
                ]}
                stats={[
                  { label: 'Total Items', value: 156, change: { value: 12, isPositive: true } },
                  { label: 'Active Items', value: 89, change: { value: 5, isPositive: true } },
                  { label: 'Archived Items', value: 67, change: { value: 3, isPositive: false } }
                ]}
              />
            </div>
          </CardContent>
        </Card>

        {/* Layout Responsiveness Test */}
        <Card>
          <CardHeader>
            <CardTitle>Responsive Layout Test</CardTitle>
            <CardDescription>Testing responsive behavior of layout components</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="p-4 border rounded-lg">
                  <h4 className="font-medium">Small Screen</h4>
                  <p className="text-sm text-muted-foreground">Content adapts to mobile</p>
                </div>
                <div className="p-4 border rounded-lg">
                  <h4 className="font-medium">Medium Screen</h4>
                  <p className="text-sm text-muted-foreground">Content adapts to tablet</p>
                </div>
                <div className="p-4 border rounded-lg">
                  <h4 className="font-medium">Large Screen</h4>
                  <p className="text-sm text-muted-foreground">Content adapts to desktop</p>
                </div>
              </div>
              
              <div className="text-center">
                <p className="text-sm text-muted-foreground">
                  Resize your browser window to see responsive behavior
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Component Integration Test */}
        <Card>
          <CardHeader>
            <CardTitle>Component Integration Test</CardTitle>
            <CardDescription>Testing how all components work together</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="p-4 bg-muted/50 rounded-lg">
                <h4 className="font-medium mb-2">Integrated Layout</h4>
                <p className="text-sm text-muted-foreground">
                  This test page demonstrates how all layout components work together to create
                  a cohesive user interface. The header, sidebar, breadcrumbs, and page headers
                  all coordinate to provide consistent navigation and layout.
                </p>
              </div>
              
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => console.log('Test button clicked')}>
                  Test Button
                </Button>
                <Button variant="outline" onClick={() => alert('Layout test successful!')}>
                  Success Test
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
};

export default LayoutTest;
