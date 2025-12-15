import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAppStore } from '../../store/appStore';
import {
  Home,
  Video,
  BookOpen,
  Brain,
  Settings,
  Menu,
  X,
  Sun,
  Moon
} from 'lucide-react';

interface NavigationProps {
  className?: string;
}

export const Navigation: React.FC<NavigationProps> = ({ className = '' }) => {
  const location = useLocation();
  const { theme, setTheme, isSidebarCollapsed, toggleSidebar } = useAppStore();

  const navigationItems = [
    { path: '/dashboard', label: 'Generator', icon: Home },
    { path: '/deployments', label: 'Deployments', icon: Video },
    { path: '/mcp/marketplace', label: 'MCP Marketplace', icon: BookOpen },
    { path: '/workflows', label: 'Workflows', icon: Brain },
  ];

  const isActivePath = (path: string) => {
    if (path === '/dashboard') {
      return location.pathname === '/dashboard' || location.pathname === '/';
    }
    return location.pathname === path;
  };

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  };

  return (
    <nav className={`bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">ER</span>
          </div>
          {!isSidebarCollapsed && (
            <span className="text-lg font-semibold text-gray-900 dark:text-white">
              EventRelay
            </span>
          )}
        </div>

        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          {isSidebarCollapsed ? (
            <Menu className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          ) : (
            <X className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          )}
        </button>
      </div>

      {/* Navigation Items */}
      <div className="p-4 space-y-2">
        {navigationItems.map((item) => {
          const Icon = item.icon;
          const isActive = isActivePath(item.path);

          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center space-x-3 px-3 py-2 rounded-lg transition-all duration-200 ${isActive
                  ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                }`}
            >
              <Icon className={`w-5 h-5 ${isActive ? 'text-blue-600 dark:text-blue-400' : ''}`} />
              {!isSidebarCollapsed && (
                <span className="font-medium">{item.label}</span>
              )}
            </Link>
          );
        })}
      </div>

      {/* Footer Actions */}
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          >
            {theme === 'light' ? (
              <Moon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            ) : (
              <Sun className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            )}
          </button>

          {/* Settings Link */}
          {!isSidebarCollapsed && (
            <Link
              to="/settings"
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              title="Settings"
            >
              <Settings className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
};
