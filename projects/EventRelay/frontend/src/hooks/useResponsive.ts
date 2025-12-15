import { useState, useEffect } from 'react';
import { useTheme, Breakpoint } from '@mui/material/styles';
import { useMediaQuery } from '@mui/material';

// Custom hook for responsive design
export const useResponsive = () => {
  const theme = useTheme();
  
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const isTablet = useMediaQuery(theme.breakpoints.between('sm', 'md'));
  const isDesktop = useMediaQuery(theme.breakpoints.up('md'));
  const isLarge = useMediaQuery(theme.breakpoints.up('lg'));
  const isXLarge = useMediaQuery(theme.breakpoints.up('xl'));

  // Get current breakpoint
  const getCurrentBreakpoint = (): Breakpoint => {
    if (isXLarge) return 'xl';
    if (isLarge) return 'lg';
    if (isDesktop) return 'md';
    if (isTablet) return 'sm';
    return 'xs';
  };

  return {
    isMobile,
    isTablet,
    isDesktop,
    isLarge,
    isXLarge,
    currentBreakpoint: getCurrentBreakpoint(),
    // Utility functions
    only: (breakpoint: Breakpoint) => useMediaQuery(theme.breakpoints.only(breakpoint)),
    up: (breakpoint: Breakpoint) => useMediaQuery(theme.breakpoints.up(breakpoint)),
    down: (breakpoint: Breakpoint) => useMediaQuery(theme.breakpoints.down(breakpoint)),
    between: (start: Breakpoint, end: Breakpoint) => useMediaQuery(theme.breakpoints.between(start, end)),
  };
};

// Hook for dynamic grid columns based on screen size
export const useResponsiveColumns = (
  mobileColumns: number = 1,
  tabletColumns: number = 2,
  desktopColumns: number = 3,
  largeColumns: number = 4
) => {
  const { isMobile, isTablet, isDesktop, isLarge } = useResponsive();

  if (isLarge) return largeColumns;
  if (isDesktop) return desktopColumns;
  if (isTablet) return tabletColumns;
  return mobileColumns;
};

// Hook for responsive spacing
export const useResponsiveSpacing = () => {
  const { isMobile, isTablet } = useResponsive();

  return {
    containerPadding: isMobile ? 2 : isTablet ? 3 : 4,
    cardSpacing: isMobile ? 2 : 3,
    sectionSpacing: isMobile ? 3 : isTablet ? 4 : 5,
    buttonSpacing: isMobile ? 1 : 2,
  };
};

// Hook for responsive typography
export const useResponsiveTypography = () => {
  const { isMobile, isTablet } = useResponsive();

  return {
    h1: isMobile ? 'h4' : isTablet ? 'h3' : 'h2',
    h2: isMobile ? 'h5' : isTablet ? 'h4' : 'h3',
    h3: isMobile ? 'h6' : isTablet ? 'h5' : 'h4',
    subtitle: isMobile ? 'body2' : 'subtitle1',
    body: isMobile ? 'body2' : 'body1',
  };
};

// Hook for responsive drawer width
export const useResponsiveDrawer = () => {
  const { isMobile, isTablet } = useResponsive();

  return {
    drawerWidth: isMobile ? '100%' : isTablet ? 280 : 320,
    drawerVariant: isMobile ? 'temporary' : 'persistent',
    showDrawerButton: isMobile || isTablet,
  };
};

// Hook for responsive dialog/modal sizing
export const useResponsiveDialog = () => {
  const { isMobile, isTablet } = useResponsive();

  return {
    maxWidth: isMobile ? 'xs' : isTablet ? 'sm' : 'md',
    fullScreen: isMobile,
    fullWidth: true,
  };
};

// Hook for touch detection
export const useTouch = () => {
  const [isTouch, setIsTouch] = useState(false);

  useEffect(() => {
    const checkTouch = () => {
      setIsTouch('ontouchstart' in window || navigator.maxTouchPoints > 0);
    };

    checkTouch();
    window.addEventListener('resize', checkTouch);

    return () => {
      window.removeEventListener('resize', checkTouch);
    };
  }, []);

  return isTouch;
};

// Hook for responsive chart dimensions
export const useResponsiveChart = () => {
  const { isMobile, isTablet } = useResponsive();

  return {
    height: isMobile ? 250 : isTablet ? 300 : 400,
    showLegend: !isMobile,
    legendPosition: isMobile ? 'bottom' : 'right',
    fontSize: isMobile ? 10 : isTablet ? 11 : 12,
  };
};

// Hook for adaptive loading states
export const useAdaptiveLoading = () => {
  const { isMobile } = useResponsive();

  return {
    skeletonVariant: isMobile ? 'text' : 'rectangular',
    skeletonAnimation: isMobile ? 'pulse' : 'wave',
    loadingDelay: isMobile ? 500 : 300, // Longer delay on mobile for better perceived performance
  };
};

// Hook for responsive table/list display
export const useResponsiveTable = () => {
  const { isMobile, isTablet } = useResponsive();

  return {
    display: isMobile ? 'cards' : 'table',
    density: isMobile ? 'compact' : isTablet ? 'standard' : 'comfortable',
    showAllColumns: !isMobile && !isTablet,
    maxVisibleColumns: isMobile ? 2 : isTablet ? 4 : 8,
  };
};

// Hook for responsive navigation
export const useResponsiveNavigation = () => {
  const { isMobile, isTablet } = useResponsive();

  return {
    showLabels: !isMobile,
    orientation: isMobile ? 'horizontal' : 'vertical',
    variant: isMobile ? 'bottom' : isTablet ? 'side-collapsed' : 'side-expanded',
    showSecondaryActions: !isMobile,
  };
};

// Hook for window dimensions
export const useWindowDimensions = () => {
  const [windowDimensions, setWindowDimensions] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });

  useEffect(() => {
    const handleResize = () => {
      setWindowDimensions({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return windowDimensions;
};

// Hook for responsive sidebar behavior
export const useResponsiveSidebar = () => {
  const { isMobile, isTablet } = useResponsive();
  const [isOpen, setIsOpen] = useState(!isMobile);

  useEffect(() => {
    // Auto-close sidebar on mobile, auto-open on desktop
    if (isMobile) {
      setIsOpen(false);
    } else if (!isTablet) {
      setIsOpen(true);
    }
  }, [isMobile, isTablet]);

  return {
    isOpen,
    setIsOpen,
    variant: isMobile ? 'temporary' : 'persistent',
    anchor: 'left',
    onClose: () => setIsOpen(false),
    onOpen: () => setIsOpen(true),
    toggle: () => setIsOpen(!isOpen),
  };
};

// Hook for responsive card layouts
export const useResponsiveCards = () => {
  const { isMobile, isTablet, isDesktop, isLarge } = useResponsive();

  const getCardColumns = () => {
    if (isLarge) return 4;
    if (isDesktop) return 3;
    if (isTablet) return 2;
    return 1;
  };

  const getCardSpacing = () => {
    if (isMobile) return 2;
    if (isTablet) return 3;
    return 4;
  };

  const getCardElevation = () => {
    return isMobile ? 2 : 3;
  };

  return {
    columns: getCardColumns(),
    spacing: getCardSpacing(),
    elevation: getCardElevation(),
    showActions: !isMobile,
    compactMode: isMobile,
  };
};

export default {
  useResponsive,
  useResponsiveColumns,
  useResponsiveSpacing,
  useResponsiveTypography,
  useResponsiveDrawer,
  useResponsiveDialog,
  useTouch,
  useResponsiveChart,
  useAdaptiveLoading,
  useResponsiveTable,
  useResponsiveNavigation,
  useWindowDimensions,
  useResponsiveSidebar,
  useResponsiveCards,
};