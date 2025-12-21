/**
 * Accessibility utilities for UVAI Platform
 * Ensures WCAG 2.1 AA compliance
 */

// ARIA labels and roles
export const ariaLabels = {
  dashboard: {
    main: 'UVAI Platform Dashboard',
    navigation: 'Main Navigation',
    projectList: 'Project List',
    statusCards: 'Status Overview Cards',
    actionButton: 'Create New Project',
  },
  videoAnalysis: {
    main: 'Video Analysis Card',
    playButton: 'Play Video',
    pauseButton: 'Pause Video',
    copyButton: 'Copy Section Content',
    bookmarkButton: 'Bookmark Section',
    completeButton: 'Mark Section Complete',
    expandButton: 'Expand Section',
    collapseButton: 'Collapse Section',
  },
  charts: {
    lineChart: 'Performance Trend Line Chart',
    barChart: 'Data Distribution Bar Chart',
    pieChart: 'Category Distribution Pie Chart',
    radarChart: 'System Metrics Radar Chart',
  },
  forms: {
    searchInput: 'Search Projects',
    filterSelect: 'Filter Options',
    sortSelect: 'Sort Options',
  },
};

// Color contrast helpers
export const colorContrast = {
  // Check if color combination meets WCAG AA standard (4.5:1)
  meetsAAStandard: (foreground: string, background: string): boolean => {
    const contrast = calculateContrastRatio(foreground, background);
    return contrast >= 4.5;
  },

  // Check if color combination meets WCAG AAA standard (7:1)
  meetsAAAStandard: (foreground: string, background: string): boolean => {
    const contrast = calculateContrastRatio(foreground, background);
    return contrast >= 7;
  },

  // Get accessible text color for a given background
  getAccessibleTextColor: (backgroundColor: string): string => {
    const lightContrast = calculateContrastRatio('#ffffff', backgroundColor);
    const darkContrast = calculateContrastRatio('#000000', backgroundColor);
    
    return lightContrast >= 4.5 ? '#ffffff' : '#000000';
  },
};

// Calculate luminance of a color
function getLuminance(hex: string): number {
  const rgb = hexToRgb(hex);
  if (!rgb) return 0;

  const [r, g, b] = [rgb.r, rgb.g, rgb.b].map(c => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });

  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

// Calculate contrast ratio between two colors
function calculateContrastRatio(foreground: string, background: string): number {
  const l1 = getLuminance(foreground);
  const l2 = getLuminance(background);
  
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  
  return (lighter + 0.05) / (darker + 0.05);
}

// Convert hex color to RGB
function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\\d]{2})([a-f\\d]{2})([a-f\\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
}

// Keyboard navigation helpers
export const keyboardNavigation = {
  // Handle keyboard navigation for interactive elements
  handleKeyDown: (event: React.KeyboardEvent, callback: () => void) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      callback();
    }
  },

  // Focus trap for modal dialogs
  trapFocus: (containerRef: React.RefObject<HTMLElement>) => {
    const focusableElements = containerRef.current?.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    if (!focusableElements || focusableElements.length === 0) return;

    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      }
    };

    document.addEventListener('keydown', handleTabKey);
    firstElement.focus();

    return () => {
      document.removeEventListener('keydown', handleTabKey);
    };
  },

  // Skip navigation for screen readers
  skipToMain: () => {
    const mainContent = document.getElementById('main-content');
    if (mainContent) {
      mainContent.focus();
      mainContent.scrollIntoView();
    }
  },
};

// Screen reader utilities
export const screenReader = {
  // Announce content changes to screen readers
  announceChange: (message: string, priority: 'polite' | 'assertive' = 'polite') => {
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', priority);
    announcement.setAttribute('aria-atomic', 'true');
    announcement.setAttribute('class', 'sr-only');
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    
    setTimeout(() => {
      document.body.removeChild(announcement);
    }, 1000);
  },

  // Update page title for context
  updatePageTitle: (title: string) => {
    document.title = `${title} - UVAI Platform`;
  },

  // Manage focus for dynamic content
  manageFocus: (element: HTMLElement | null) => {
    if (element) {
      element.focus();
      // Add temporary tabindex if element is not focusable
      if (!element.hasAttribute('tabindex')) {
        element.setAttribute('tabindex', '-1');
        element.addEventListener('blur', () => {
          element.removeAttribute('tabindex');
        }, { once: true });
      }
    }
  },
};

// Responsive design breakpoints
export const breakpoints = {
  mobile: 320,
  tablet: 768,
  desktop: 1024,
  large: 1440,
};

// Touch interaction helpers
export const touchInteraction = {
  // Ensure touch targets are at least 44x44px
  minTouchTarget: 44,

  // Add appropriate spacing between touch targets
  touchTargetSpacing: 8,

  // Handle touch gestures
  handleSwipe: (
    element: HTMLElement,
    onSwipeLeft?: () => void,
    onSwipeRight?: () => void
  ) => {
    let startX: number;
    let startY: number;

    const handleTouchStart = (e: TouchEvent) => {
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
    };

    const handleTouchEnd = (e: TouchEvent) => {
      if (!startX || !startY) return;

      const endX = e.changedTouches[0].clientX;
      const endY = e.changedTouches[0].clientY;

      const deltaX = endX - startX;
      const deltaY = endY - startY;

      // Only trigger swipe if horizontal movement is greater than vertical
      if (Math.abs(deltaX) > Math.abs(deltaY)) {
        const threshold = 50;
        
        if (deltaX > threshold && onSwipeRight) {
          onSwipeRight();
        } else if (deltaX < -threshold && onSwipeLeft) {
          onSwipeLeft();
        }
      }
    };

    element.addEventListener('touchstart', handleTouchStart, { passive: true });
    element.addEventListener('touchend', handleTouchEnd, { passive: true });

    return () => {
      element.removeEventListener('touchstart', handleTouchStart);
      element.removeEventListener('touchend', handleTouchEnd);
    };
  },
};

// High contrast mode detection
export const highContrast = {
  // Detect if user prefers high contrast
  prefersHighContrast: (): boolean => {
    return window.matchMedia('(prefers-contrast: high)').matches;
  },

  // Detect if user prefers reduced motion
  prefersReducedMotion: (): boolean => {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  },

  // Apply high contrast styles
  applyHighContrastTheme: () => {
    document.documentElement.setAttribute('data-high-contrast', 'true');
  },

  // Remove high contrast styles
  removeHighContrastTheme: () => {
    document.documentElement.removeAttribute('data-high-contrast');
  },
};

// Form accessibility helpers
export const formAccessibility = {
  // Generate unique IDs for form elements
  generateId: (prefix: string): string => {
    return `${prefix}-${Math.random().toString(36).substr(2, 9)}`;
  },

  // Validate required fields and announce errors
  validateAndAnnounce: (
    formData: Record<string, any>,
    requiredFields: string[]
  ): string[] => {
    const errors: string[] = [];
    
    requiredFields.forEach(field => {
      if (!formData[field] || (typeof formData[field] === 'string' && formData[field].trim() === '')) {
        errors.push(`${field} is required`);
      }
    });

    if (errors.length > 0) {
      screenReader.announceChange(
        `Form validation failed. ${errors.length} error${errors.length > 1 ? 's' : ''} found.`,
        'assertive'
      );
    }

    return errors;
  },

  // Focus first error field
  focusFirstError: (formElement: HTMLFormElement) => {
    const firstError = formElement.querySelector('[aria-invalid="true"]') as HTMLElement;
    if (firstError) {
      screenReader.manageFocus(firstError);
    }
  },
};

// Export all utilities as default
export default {
  ariaLabels,
  colorContrast,
  keyboardNavigation,
  screenReader,
  breakpoints,
  touchInteraction,
  highContrast,
  formAccessibility,
};