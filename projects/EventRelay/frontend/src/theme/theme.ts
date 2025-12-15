import { createTheme, Theme } from '@mui/material/styles';
import { alpha } from '@mui/material/styles';

declare module '@mui/material/styles' {
  interface Palette {
    video: {
      main: string;
      light: string;
      dark: string;
      contrastText: string;
    };
    analytics: {
      main: string;
      light: string;
      dark: string;
      contrastText: string;
    };
  }

  interface PaletteOptions {
    video?: {
      main: string;
      light: string;
      dark: string;
      contrastText: string;
    };
    analytics?: {
      main: string;
      light: string;
      dark: string;
      contrastText: string;
    };
  }
}

// Define color palette for UVAI platform
const colors = {
  primary: {
    50: '#e3f2fd',
    100: '#bbdefb',
    200: '#90caf9',
    300: '#64b5f6',
    400: '#42a5f5',
    500: '#2196f3',
    600: '#1e88e5',
    700: '#1976d2',
    800: '#1565c0',
    900: '#0d47a1',
  },
  secondary: {
    50: '#f3e5f5',
    100: '#e1bee7',
    200: '#ce93d8',
    300: '#ba68c8',
    400: '#ab47bc',
    500: '#9c27b0',
    600: '#8e24aa',
    700: '#7b1fa2',
    800: '#6a1b9a',
    900: '#4a148c',
  },
  video: {
    50: '#fff3e0',
    100: '#ffe0b2',
    200: '#ffcc80',
    300: '#ffb74d',
    400: '#ffa726',
    500: '#ff9800',
    600: '#fb8c00',
    700: '#f57c00',
    800: '#ef6c00',
    900: '#e65100',
  },
  analytics: {
    50: '#e8f5e8',
    100: '#c8e6c9',
    200: '#a5d6a7',
    300: '#81c784',
    400: '#66bb6a',
    500: '#4caf50',
    600: '#43a047',
    700: '#388e3c',
    800: '#2e7d32',
    900: '#1b5e20',
  },
};

const baseTheme = createTheme({
  palette: {
    primary: {
      main: colors.primary[600],
      light: colors.primary[400],
      dark: colors.primary[800],
      contrastText: '#ffffff',
    },
    secondary: {
      main: colors.secondary[600],
      light: colors.secondary[400],
      dark: colors.secondary[800],
      contrastText: '#ffffff',
    },
    video: {
      main: colors.video[600],
      light: colors.video[400],
      dark: colors.video[800],
      contrastText: '#ffffff',
    },
    analytics: {
      main: colors.analytics[600],
      light: colors.analytics[400],
      dark: colors.analytics[800],
      contrastText: '#ffffff',
    },
    background: {
      default: '#fafafa',
      paper: '#ffffff',
    },
    text: {
      primary: 'rgba(0, 0, 0, 0.87)',
      secondary: 'rgba(0, 0, 0, 0.6)',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '3.5rem',
      fontWeight: 600,
      lineHeight: 1.2,
      letterSpacing: '-0.02em',
    },
    h2: {
      fontSize: '2.5rem',
      fontWeight: 600,
      lineHeight: 1.3,
      letterSpacing: '-0.01em',
    },
    h3: {
      fontSize: '2rem',
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 600,
      lineHeight: 1.5,
    },
    h6: {
      fontSize: '1.125rem',
      fontWeight: 600,
      lineHeight: 1.5,
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.6,
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.6,
    },
    button: {
      textTransform: 'none' as const,
      fontWeight: 500,
    },
  },
  shape: {
    borderRadius: 12,
  },
  spacing: 8,
});

export const lightTheme = createTheme({
  ...baseTheme,
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 8px 0 rgba(99, 99, 99, 0.2)',
          borderRadius: 16,
          transition: 'box-shadow 0.3s ease, transform 0.2s ease',
          '&:hover': {
            boxShadow: '0 4px 16px 0 rgba(99, 99, 99, 0.3)',
            transform: 'translateY(-2px)',
          },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: '10px 24px',
          fontSize: '0.875rem',
          fontWeight: 500,
          textTransform: 'none',
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0 2px 8px 0 rgba(25, 118, 210, 0.3)',
          },
        },
        contained: {
          '&:hover': {
            boxShadow: '0 4px 12px 0 rgba(25, 118, 210, 0.4)',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontWeight: 500,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
        },
        elevation1: {
          boxShadow: '0 2px 8px 0 rgba(99, 99, 99, 0.2)',
        },
        elevation2: {
          boxShadow: '0 4px 16px 0 rgba(99, 99, 99, 0.2)',
        },
        elevation3: {
          boxShadow: '0 8px 24px 0 rgba(99, 99, 99, 0.2)',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
          backgroundColor: colors.primary[700],
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRadius: 0,
          borderRight: `1px solid ${alpha('#000', 0.12)}`,
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          height: 6,
        },
      },
    },
    MuiCircularProgress: {
      styleOverrides: {
        root: {
          animationDuration: '1.4s',
        },
      },
    },
  },
});

export const darkTheme = createTheme({
  ...baseTheme,
  palette: {
    ...baseTheme.palette,
    mode: 'dark',
    background: {
      default: '#0a0a0a',
      paper: '#1a1a1a',
    },
    text: {
      primary: 'rgba(255, 255, 255, 0.87)',
      secondary: 'rgba(255, 255, 255, 0.6)',
    },
    primary: {
      main: colors.primary[400],
      light: colors.primary[300],
      dark: colors.primary[700],
      contrastText: '#ffffff',
    },
    secondary: {
      main: colors.secondary[400],
      light: colors.secondary[300],
      dark: colors.secondary[700],
      contrastText: '#ffffff',
    },
    video: {
      main: colors.video[400],
      light: colors.video[300],
      dark: colors.video[700],
      contrastText: '#000000',
    },
    analytics: {
      main: colors.analytics[400],
      light: colors.analytics[300],
      dark: colors.analytics[700],
      contrastText: '#000000',
    },
  },
  components: {
    ...lightTheme.components,
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: '#1a1a1a',
          boxShadow: '0 2px 8px 0 rgba(0, 0, 0, 0.4)',
          borderRadius: 16,
          transition: 'box-shadow 0.3s ease, transform 0.2s ease',
          '&:hover': {
            boxShadow: '0 4px 16px 0 rgba(0, 0, 0, 0.6)',
            transform: 'translateY(-2px)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: '#1a1a1a',
          borderRadius: 16,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#1a1a1a',
          borderBottom: `1px solid ${alpha('#fff', 0.12)}`,
        },
      },
    },
  },
});

export type UVAITheme = Theme;
export { colors };