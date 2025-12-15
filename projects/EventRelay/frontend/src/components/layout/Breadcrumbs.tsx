'use client';

import React from 'react';
import { ChevronRight, Home, Folder, FileText, Video, BarChart3, Settings } from 'lucide-react';
import { Button } from '../ui/button';
import { cn } from '../../lib/utils';

interface BreadcrumbItem {
  label: string;
  href?: string;
  icon?: React.ReactNode;
  isActive?: boolean;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  className?: string;
  showHome?: boolean;
  maxItems?: number;
  separator?: React.ReactNode;
}

// Icon mapping for common routes
const getRouteIcon = (path: string) => {
  if (path.includes('/videos')) return <Video className="h-4 w-4" />;
  if (path.includes('/content')) return <FileText className="h-4 w-4" />;
  if (path.includes('/analytics')) return <BarChart3 className="h-4 w-4" />;
  if (path.includes('/settings')) return <Settings className="h-4 w-4" />;
  if (path.includes('/folders')) return <Folder className="h-4 w-4" />;
  return null;
};

export const Breadcrumbs: React.FC<BreadcrumbsProps> = ({
  items,
  className,
  showHome = true,
  maxItems = 5,
  separator = <ChevronRight className="h-4 w-4 text-muted-foreground" />
}) => {
  // Add home item if enabled
  const allItems: BreadcrumbItem[] = showHome 
    ? [{ label: 'Home', href: '/', icon: <Home className="h-4 w-4" /> }, ...items]
    : items;

  // Limit items if maxItems is specified
  const displayItems: BreadcrumbItem[] = maxItems ? allItems.slice(-maxItems) : allItems;

  // If we're limiting items, add ellipsis for truncated items
  const hasTruncatedItems = maxItems && allItems.length > maxItems;

  return (
    <nav
      aria-label="Breadcrumb"
      className={cn(
        "flex items-center space-x-1 text-sm text-muted-foreground",
        className
      )}
    >
      {hasTruncatedItems && (
        <>
          <span className="px-2 py-1 text-xs bg-muted rounded-md">
            ...
          </span>
          {separator}
        </>
      )}

      {displayItems.map((item, index) => {
        const isLast = index === displayItems.length - 1;
        const isActive = item.isActive !== undefined ? item.isActive : isLast;

        return (
          <React.Fragment key={item.label}>
            <div className="flex items-center gap-2">
              {item.icon && (
                <span className="flex-shrink-0">
                  {item.icon}
                </span>
              )}
              
              {item.href && !isActive ? (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto p-1 text-sm font-normal hover:text-foreground"
                  onClick={() => {
                    // Handle navigation
                    if (typeof window !== 'undefined') {
                      window.location.href = item.href!;
                    }
                  }}
                >
                  {item.label}
                </Button>
              ) : (
                <span
                  className={cn(
                    "px-2 py-1 rounded-md",
                    isActive 
                      ? "text-foreground font-medium bg-accent" 
                      : "text-muted-foreground"
                  )}
                >
                  {item.label}
                </span>
              )}
            </div>

            {!isLast && (
              <span className="flex-shrink-0">
                {separator}
              </span>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
};

// Auto-generate breadcrumbs from current pathname
export const AutoBreadcrumbs: React.FC<{
  pathname?: string;
  className?: string;
  showHome?: boolean;
  maxItems?: number;
}> = ({ 
  pathname = typeof window !== 'undefined' ? window.location.pathname : '/',
  className,
  showHome = true,
  maxItems = 5
}) => {
  const generateBreadcrumbs = (path: string): BreadcrumbItem[] => {
    const segments = path.split('/').filter(Boolean);
    
    if (segments.length === 0) {
      return [];
    }

    return segments.map((segment, index) => {
      const href = '/' + segments.slice(0, index + 1).join('/');
      const label = segment
        .split('-')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');

      return {
        label,
        href,
        icon: getRouteIcon(href),
        isActive: index === segments.length - 1
      };
    });
  };

  const breadcrumbItems = generateBreadcrumbs(pathname);

  return (
    <Breadcrumbs
      items={breadcrumbItems}
      className={className}
      showHome={showHome}
      maxItems={maxItems}
    />
  );
};

// Specialized breadcrumb components for common sections
export const VideoBreadcrumbs: React.FC<{
  videoTitle?: string;
  folderName?: string;
  className?: string;
}> = ({ videoTitle, folderName, className }) => {
  const items: BreadcrumbItem[] = [
    { label: 'Videos', href: '/videos', icon: <Video className="h-4 w-4" /> }
  ];

  if (folderName) {
    items.push({ 
      label: folderName, 
      href: `/videos/folders/${folderName.toLowerCase().replace(/\s+/g, '-')}`,
      icon: <Folder className="h-4 w-4" />
    });
  }

  if (videoTitle) {
    items.push({ 
      label: videoTitle, 
      icon: <Video className="h-4 w-4" />,
      isActive: true
    });
  }

  return <Breadcrumbs items={items} className={className} />;
};

export const ContentBreadcrumbs: React.FC<{
  contentType?: 'transcripts' | 'summaries' | 'insights';
  contentTitle?: string;
  className?: string;
}> = ({ contentType, contentTitle, className }) => {
  const items: BreadcrumbItem[] = [
    { label: 'Content', href: '/content', icon: <FileText className="h-4 w-4" /> }
  ];

  if (contentType) {
    const contentTypeLabel = contentType.charAt(0).toUpperCase() + contentType.slice(1);
    items.push({ 
      label: contentTypeLabel, 
      href: `/content/${contentType}`,
      icon: <FileText className="h-4 w-4" />
    });
  }

  if (contentTitle) {
    items.push({ 
      label: contentTitle, 
      icon: <FileText className="h-4 w-4" />,
      isActive: true
    });
  }

  return <Breadcrumbs items={items} className={className} />;
};

export const AnalyticsBreadcrumbs: React.FC<{
  reportType?: 'overview' | 'performance' | 'reports';
  reportName?: string;
  className?: string;
}> = ({ reportType, reportName, className }) => {
  const items: BreadcrumbItem[] = [
    { label: 'Analytics', href: '/analytics', icon: <BarChart3 className="h-4 w-4" /> }
  ];

  if (reportType) {
    const reportTypeLabel = reportType.charAt(0).toUpperCase() + reportType.slice(1);
    items.push({ 
      label: reportTypeLabel, 
      href: `/analytics/${reportType}`,
      icon: <BarChart3 className="h-4 w-4" />
    });
  }

  if (reportName) {
    items.push({ 
      label: reportName, 
      icon: <BarChart3 className="h-4 w-4" />,
      isActive: true
    });
  }

  return <Breadcrumbs items={items} className={className} />;
};

// Export types
export type { BreadcrumbItem };
