'use client';

import React from 'react';
import { 
  Plus, 
  Download, 
  Share2, 
  MoreHorizontal, 
  ArrowLeft,
  RefreshCw,
  Settings,
  Filter,
  Search
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Separator } from '../ui/separator';
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuLabel, 
  DropdownMenuSeparator, 
  DropdownMenuTrigger 
} from '../ui/dropdown-menu';
import { Breadcrumbs, BreadcrumbItem } from './Breadcrumbs';
import { cn } from '../../lib/utils';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  breadcrumbs?: BreadcrumbItem[];
  showBreadcrumbs?: boolean;
  actions?: React.ReactNode;
  backButton?: {
    href: string;
    label: string;
  };
  search?: {
    placeholder?: string;
    value?: string;
    onChange?: (value: string) => void;
    onSearch?: (query: string) => void;
  };
  filters?: {
    label: string;
    options: { value: string; label: string }[];
    value?: string;
    onChange?: (value: string) => void;
  }[];
  stats?: {
    label: string;
    value: string | number;
    change?: {
      value: number;
      isPositive: boolean;
    };
  }[];
  className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  breadcrumbs = [],
  showBreadcrumbs = true,
  actions,
  backButton,
  search,
  filters,
  stats,
  className
}) => {
  const [searchValue, setSearchValue] = React.useState(search?.value || '');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (search?.onSearch) {
      search.onSearch(searchValue);
    }
  };

  return (
    <div className={cn("space-y-6", className)}>
      {/* Breadcrumbs */}
      {showBreadcrumbs && breadcrumbs.length > 0 && (
        <Breadcrumbs items={breadcrumbs} />
      )}

      {/* Main Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex-1 min-w-0">
          {/* Back Button */}
          {backButton && (
            <div className="mb-4">
              <Button
                variant="ghost"
                size="sm"
                className="gap-2 text-muted-foreground hover:text-foreground"
                onClick={() => {
                  if (typeof window !== 'undefined') {
                    window.location.href = backButton.href;
                  }
                }}
              >
                <ArrowLeft className="h-4 w-4" />
                {backButton.label}
              </Button>
            </div>
          )}

          {/* Title and Subtitle */}
          <div className="space-y-2">
            <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
            {subtitle && (
              <p className="text-lg text-muted-foreground">{subtitle}</p>
            )}
          </div>
        </div>

        {/* Actions */}
        {actions && (
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            {actions}
          </div>
        )}
      </div>

      {/* Search and Filters Bar */}
      {(search || filters) && (
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          {/* Search */}
          {search && (
            <form onSubmit={handleSearch} className="flex-1 max-w-md">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                <Input
                  placeholder={search.placeholder || "Search..."}
                  value={searchValue}
                  onChange={(e) => {
                    setSearchValue(e.target.value);
                    search.onChange?.(e.target.value);
                  }}
                  className="pl-10"
                />
              </div>
            </form>
          )}

          {/* Filters */}
          {filters && filters.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {filters.map((filter, index) => (
                <div key={index} className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground whitespace-nowrap">
                    {filter.label}:
                  </span>
                  <select
                    value={filter.value || ''}
                    onChange={(e) => filter.onChange?.(e.target.value)}
                    className="px-3 py-1 text-sm border rounded-md bg-background"
                  >
                    <option value="">All</option>
                    {filter.options.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Stats */}
      {stats && stats.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat, index) => (
            <div key={index} className="p-4 bg-muted/50 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">{stat.label}</span>
                {stat.change && (
                  <Badge 
                    variant={stat.change.isPositive ? "default" : "secondary"}
                    className="text-xs"
                  >
                    {stat.change.isPositive ? '+' : ''}{stat.change.value}%
                  </Badge>
                )}
              </div>
              <p className="text-2xl font-bold mt-1">{stat.value}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Specialized page headers for common use cases
export const VideoPageHeader: React.FC<{
  title: string;
  subtitle?: string;
  folderName?: string;
  videoCount?: number;
  actions?: React.ReactNode;
  search?: PageHeaderProps['search'];
  filters?: PageHeaderProps['filters'];
}> = ({ 
  title, 
  subtitle, 
  folderName, 
  videoCount, 
  actions, 
  search, 
  filters 
}) => {
  const breadcrumbs: BreadcrumbItem[] = [
    { label: 'Videos', href: '/videos' }
  ];

  if (folderName) {
    breadcrumbs.push({ 
      label: folderName, 
      href: `/videos/folders/${folderName.toLowerCase().replace(/\s+/g, '-')}` 
    });
  }

  const stats = videoCount !== undefined ? [
    {
      label: 'Total Videos',
      value: videoCount
    }
  ] : undefined;

  return (
    <PageHeader
      title={title}
      subtitle={subtitle}
      breadcrumbs={breadcrumbs}
      actions={actions}
      search={search}
      filters={filters}
      stats={stats}
    />
  );
};

export const ContentPageHeader: React.FC<{
  title: string;
  subtitle?: string;
  contentType: 'transcripts' | 'summaries' | 'insights';
  contentCount?: number;
  actions?: React.ReactNode;
  search?: PageHeaderProps['search'];
  filters?: PageHeaderProps['filters'];
}> = ({ 
  title, 
  subtitle, 
  contentType, 
  contentCount, 
  actions, 
  search, 
  filters 
}) => {
  const contentTypeLabel = contentType.charAt(0).toUpperCase() + contentType.slice(1);
  
  const breadcrumbs: BreadcrumbItem[] = [
    { label: 'Content', href: '/content' },
    { label: contentTypeLabel, href: `/content/${contentType}` }
  ];

  const stats = contentCount !== undefined ? [
    {
      label: `Total ${contentTypeLabel}`,
      value: contentCount
    }
  ] : undefined;

  return (
    <PageHeader
      title={title}
      subtitle={subtitle}
      breadcrumbs={breadcrumbs}
      actions={actions}
      search={search}
      filters={filters}
      stats={stats}
    />
  );
};

export const AnalyticsPageHeader: React.FC<{
  title: string;
  subtitle?: string;
  reportType: 'overview' | 'performance' | 'reports';
  actions?: React.ReactNode;
  search?: PageHeaderProps['search'];
  filters?: PageHeaderProps['filters'];
}> = ({ 
  title, 
  subtitle, 
  reportType, 
  actions, 
  search, 
  filters 
}) => {
  const reportTypeLabel = reportType.charAt(0).toUpperCase() + reportType.slice(1);
  
  const breadcrumbs: BreadcrumbItem[] = [
    { label: 'Analytics', href: '/analytics' },
    { label: reportTypeLabel, href: `/analytics/${reportType}` }
  ];

  return (
    <PageHeader
      title={title}
      subtitle={subtitle}
      breadcrumbs={breadcrumbs}
      actions={actions}
      search={search}
      filters={filters}
    />
  );
};

// Common action buttons
export const CommonActions = {
  Upload: ({ onClick }: { onClick?: () => void }) => (
    <Button onClick={onClick} className="gap-2">
      <Plus className="h-4 w-4" />
      Upload
    </Button>
  ),
  
  Download: ({ onClick }: { onClick?: () => void }) => (
    <Button variant="outline" onClick={onClick} className="gap-2">
      <Download className="h-4 w-4" />
      Download
    </Button>
  ),
  
  Share: ({ onClick }: { onClick?: () => void }) => (
    <Button variant="outline" onClick={onClick} className="gap-2">
      <Share2 className="h-4 w-4" />
      Share
    </Button>
  ),
  
  Refresh: ({ onClick, loading }: { onClick?: () => void; loading?: boolean }) => (
    <Button variant="outline" onClick={onClick} disabled={loading} className="gap-2">
      <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
      Refresh
    </Button>
  ),
  
  Settings: ({ onClick }: { onClick?: () => void }) => (
    <Button variant="outline" onClick={onClick} className="gap-2">
      <Settings className="h-4 w-4" />
      Settings
    </Button>
  ),
  
  More: ({ children }: { children: React.ReactNode }) => (
    <DropdownMenu>
      <DropdownMenuTrigger>
        <Button variant="outline" size="icon">
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {children}
      </DropdownMenuContent>
    </DropdownMenu>
  )
};
