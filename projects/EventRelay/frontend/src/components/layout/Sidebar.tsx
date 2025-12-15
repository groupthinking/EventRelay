'use client';

import React, { useState, useEffect } from 'react';
import {
  Video,
  FileText,
  BarChart3,
  Settings,
  Home,
  Upload,
  Play,
  Clock,
  Star,
  Folder,
  ChevronRight,
  ChevronDown,
  Plus,
  Search,
  Filter,
  Calendar,
  Tag,
  Users,
  Zap,
  BookOpen,
  Target,
  TrendingUp,
  Activity,
  Database,
  Cloud,
  Shield,
  HelpCircle,
  MessageSquare,
  ExternalLink,
  X,
  CheckCircle,
  ShoppingBag
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Separator } from '../ui/separator';
import { cn } from '../../lib/utils';


interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  className?: string;
}

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  href?: string;
  badge?: string | number;
  children?: NavItem[];
  isExpanded?: boolean;
}

interface QuickAction {
  id: string;
  label: string;
  icon: React.ReactNode;
  href: string;
  description: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  className
}) => {
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPath, setCurrentPath] = useState('/dashboard');

  // Navigation items optimized for Infrastructure Generation
  const navigationItems: NavItem[] = [
    {
      id: 'generator',
      label: 'Generator Console',
      icon: <Zap className="h-4 w-4" />,
      href: '/dashboard'
    },
    {
      id: 'deployments',
      label: 'Deployments',
      icon: <Cloud className="h-4 w-4" />,
      href: '/deployments',
      badge: 'Active'
    },
    {
      id: 'mcp-servers',
      label: 'MCP Servers',
      icon: <Database className="h-4 w-4" />,
      children: [
        { id: 'installed', label: 'Installed', href: '/mcp/installed', icon: <CheckCircle className="h-4 w-4" /> },
        { id: 'marketplace', label: 'Marketplace', href: '/mcp/marketplace', icon: <ShoppingBag className="h-4 w-4" /> }
      ]
    },
    {
      id: 'workflows',
      label: 'Workflows',
      icon: <Activity className="h-4 w-4" />,
      href: '/workflows'
    },
    {
      id: 'documentation',
      label: 'Documentation',
      icon: <BookOpen className="h-4 w-4" />,
      href: '/docs'
    }
  ];

  // Quick actions for common tasks
  const quickActions: QuickAction[] = [
    {
      id: 'upload-video',
      label: 'Upload Video',
      icon: <Upload className="h-4 w-4" />,
      href: '/upload',
      description: 'Upload a new video for processing'
    },
    {
      id: 'create-folder',
      label: 'Create Folder',
      icon: <Folder className="h-4 w-4" />,
      href: '/folders/create',
      description: 'Organize your videos in folders'
    },
    {
      id: 'generate-report',
      label: 'Generate Report',
      icon: <BarChart3 className="h-4 w-4" />,
      href: '/reports/generate',
      description: 'Create custom analytics reports'
    }
  ];

  // Filtered navigation items based on search
  const filteredNavigation = navigationItems.filter(item =>
    item.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.children?.some(child =>
      child.label.toLowerCase().includes(searchQuery.toLowerCase())
    )
  );

  const toggleSection = (sectionId: string) => {
    setCollapsedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sectionId)) {
        newSet.delete(sectionId);
      } else {
        newSet.add(sectionId);
      }
      return newSet;
    });
  };

  const isSectionCollapsed = (sectionId: string) => collapsedSections.has(sectionId);

  const handleNavigation = (href: string) => {
    setCurrentPath(href);
    // Close sidebar on mobile after navigation
    if (window.innerWidth < 1024) {
      onClose();
    }
  };

  const isActive = (href: string) => currentPath === href;

  // Close sidebar when clicking outside on mobile
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (isOpen && window.innerWidth < 1024) {
        const sidebar = document.getElementById('sidebar');
        if (sidebar && !sidebar.contains(event.target as Node)) {
          onClose();
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, onClose]);

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        id="sidebar"
        className={cn(
          "fixed left-0 top-0 z-50 h-full w-64 transform bg-background border-r transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0",
          isOpen ? "translate-x-0" : "-translate-x-full",
          className
        )}
      >
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="flex h-16 items-center justify-between px-4 border-b">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-lg flex items-center justify-center">
                <Video className="w-5 h-5 text-white" />
              </div>
              <span className="font-bold text-lg">EventRelay</span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="lg:hidden"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Search */}
          <div className="p-4 border-b">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
              <Input
                placeholder="Search navigation..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          {/* Quick Actions */}
          <div className="p-4 border-b">
            <h3 className="text-sm font-semibold text-muted-foreground mb-3">
              Quick Actions
            </h3>
            <div className="space-y-2">
              {quickActions.map((action) => (
                <Button
                  key={action.id}
                  variant="ghost"
                  className="w-full justify-start h-auto p-3"
                  onClick={() => handleNavigation(action.href)}
                >
                  <div className="flex items-start gap-3 text-left">
                    <div className="mt-0.5">{action.icon}</div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm">{action.label}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {action.description}
                      </p>
                    </div>
                  </div>
                </Button>
              ))}
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto p-4">
            <div className="space-y-2">
              {filteredNavigation.map((item) => (
                <div key={item.id}>
                  {item.children ? (
                    // Section with children
                    <div>
                      <Button
                        variant="ghost"
                        className="w-full justify-between h-auto p-3"
                        onClick={() => toggleSection(item.id)}
                      >
                        <div className="flex items-center gap-3">
                          {item.icon}
                          <span className="font-medium">{item.label}</span>
                          {item.badge && (
                            <Badge variant="secondary" className="ml-auto">
                              {item.badge}
                            </Badge>
                          )}
                        </div>
                        {isSectionCollapsed(item.id) ? (
                          <ChevronRight className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </Button>

                      {!isSectionCollapsed(item.id) && (
                        <div className="ml-6 mt-1 space-y-1">
                          {item.children.map((child) => (
                            <Button
                              key={child.id}
                              variant="ghost"
                              size="sm"
                              className={cn(
                                "w-full justify-start h-auto p-2 text-sm",
                                isActive(child.href || '') && "bg-accent text-accent-foreground"
                              )}
                              onClick={() => handleNavigation(child.href || '')}
                            >
                              <div className="flex items-center gap-2">
                                {child.icon}
                                <span>{child.label}</span>
                              </div>
                            </Button>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    // Single navigation item
                    <Button
                      variant="ghost"
                      className={cn(
                        "w-full justify-start h-auto p-3",
                        isActive(item.href || '') && "bg-accent text-accent-foreground"
                      )}
                      onClick={() => handleNavigation(item.href || '')}
                    >
                      <div className="flex items-center gap-3">
                        {item.icon}
                        <span className="font-medium">{item.label}</span>
                        {item.badge && (
                          <Badge variant="secondary" className="ml-auto">
                            {item.badge}
                          </Badge>
                        )}
                      </div>
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </nav>

          {/* Footer */}
          <div className="p-4 border-t">
            <div className="space-y-2">
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start"
                onClick={() => handleNavigation('/settings')}
              >
                <Settings className="mr-2 h-4 w-4" />
                Settings
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start"
                onClick={() => handleNavigation('/help')}
              >
                <HelpCircle className="mr-2 h-4 w-4" />
                Help & Support
              </Button>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
