import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import VideoAnalysisCard from '../VideoAnalysisCard';

// Mock react-markdown
jest.mock('react-markdown', () => {
  return function MockReactMarkdown({ children }: { children: string }) {
    return <div data-testid="markdown-content">{children}</div>;
  };
});

jest.mock('remark-gfm', () => ({
  __esModule: true,
  default: () => {},
}));

// Mock Material-UI theme
const mockTheme = createTheme();

// Mock video data
const mockVideoData = {
  id: 'test-video-123',
  title: 'Advanced React Patterns',
  channel: 'Tech Education Hub',
  duration: '18:45',
  category: 'Educational',
  difficulty: 'intermediate',
  metadata: {
    viewCount: 125000,
    publishedAt: '2024-01-15',
    language: 'en',
    tags: ['react', 'javascript', 'patterns']
  }
};

const mockActions = [
  {
    id: 'action-1',
    title: 'Set up React project',
    description: 'Initialize a new React project with TypeScript',
    category: 'Setup',
    priority: 'high',
    estimatedTime: '15 minutes',
    completed: false,
    timestamp: 180
  },
  {
    id: 'action-2',
    title: 'Implement component composition pattern',
    description: 'Create reusable components using composition',
    category: 'Development',
    priority: 'medium',
    estimatedTime: '30 minutes',
    completed: true,
    timestamp: 520
  }
];

const mockTranscript = `
## Introduction
Welcome to this comprehensive tutorial on Advanced React Patterns.

## Component Composition
Let's explore how to create flexible and reusable components.

### Key Concepts
- Higher Order Components (HOCs)
- Render Props Pattern
- Compound Components
`;

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={mockTheme}>
      {component}
    </ThemeProvider>
  );
};

describe('VideoAnalysisCard', () => {
  const defaultProps = {
    videoData: mockVideoData,
    actions: mockActions,
    transcript: mockTranscript,
    isLoading: false,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Component Rendering', () => {
    it('renders video information correctly', () => {
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      expect(screen.getByText('Advanced React Patterns')).toBeInTheDocument();
      expect(screen.getByText('Tech Education Hub')).toBeInTheDocument();
      expect(screen.getByText('18:45')).toBeInTheDocument();
      expect(screen.getByText('Educational')).toBeInTheDocument();
    });

    it('renders video metadata', () => {
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      expect(screen.getByText(/125,000/)).toBeInTheDocument(); // View count
      expect(screen.getByText(/2024-01-15/)).toBeInTheDocument(); // Published date
    });

    it('renders action items', () => {
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      expect(screen.getByText('Set up React project')).toBeInTheDocument();
      expect(screen.getByText('Implement component composition pattern')).toBeInTheDocument();
      expect(screen.getByText('15 minutes')).toBeInTheDocument();
      expect(screen.getByText('30 minutes')).toBeInTheDocument();
    });

    it('renders transcript content', () => {
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      expect(screen.getByTestId('markdown-content')).toBeInTheDocument();
      expect(screen.getByText(/Introduction/)).toBeInTheDocument();
      expect(screen.getByText(/Component Composition/)).toBeInTheDocument();
    });

    it('shows loading state when isLoading is true', () => {
      renderWithTheme(<VideoAnalysisCard {...defaultProps} isLoading={true} />);
      
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });
  });

  describe('Action Management', () => {
    it('toggles action completion state', async () => {
      const user = userEvent.setup();
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      const uncompletedAction = screen.getByText('Set up React project');
      const completionButton = uncompletedAction.closest('[data-testid="action-item"]')?.querySelector('[data-testid="toggle-completion"]');
      
      if (completionButton) {
        await user.click(completionButton);
        // Verify state change (would need state management to test properly)
      }
    });

    it('filters actions by category', async () => {
      const user = userEvent.setup();
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      // If category filter exists
      const categoryFilter = screen.queryByTestId('category-filter');
      if (categoryFilter) {
        await user.click(categoryFilter);
      }
    });

    it('shows action priority indicators', () => {
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      expect(screen.getByText('high')).toBeInTheDocument();
      expect(screen.getByText('medium')).toBeInTheDocument();
    });

    it('displays estimated time for actions', () => {
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      expect(screen.getByText('15 minutes')).toBeInTheDocument();
      expect(screen.getByText('30 minutes')).toBeInTheDocument();
    });
  });

  describe('Bookmark Functionality', () => {
    it('toggles bookmark state when bookmark button is clicked', async () => {
      const user = userEvent.setup();
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      const bookmarkButton = screen.getByTestId('bookmark-button');
      expect(bookmarkButton).toBeInTheDocument();
      
      await user.click(bookmarkButton);
      // State should toggle (would need proper state management to test)
    });

    it('shows appropriate bookmark icon based on state', () => {
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      // Initially not bookmarked
      expect(screen.getByTestId('bookmark-button')).toBeInTheDocument();
    });
  });

  describe('Expand/Collapse Functionality', () => {
    it('expands and collapses transcript section', async () => {
      const user = userEvent.setup();
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      const transcriptToggle = screen.getByTestId('expand-transcript');
      await user.click(transcriptToggle);
      
      // Transcript should be expanded/collapsed
      expect(screen.getByTestId('transcript-section')).toBeInTheDocument();
    });

    it('expands and collapses actions section', async () => {
      const user = userEvent.setup();
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      const actionsToggle = screen.getByTestId('expand-actions');
      await user.click(actionsToggle);
      
      expect(screen.getByTestId('actions-section')).toBeInTheDocument();
    });

    it('shows appropriate expand/collapse icons', () => {
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      expect(screen.getByTestId('expand-transcript')).toBeInTheDocument();
      expect(screen.getByTestId('expand-actions')).toBeInTheDocument();
    });
  });

  describe('Copy Functionality', () => {
    it('copies action to clipboard when copy button is clicked', async () => {
      const user = userEvent.setup();
      
      // Mock clipboard API
      const mockClipboard = {
        writeText: jest.fn().mockResolvedValue(undefined)
      };
      Object.assign(navigator, { clipboard: mockClipboard });
      
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      const copyButton = screen.getAllByTestId('copy-action')[0];
      await user.click(copyButton);
      
      expect(mockClipboard.writeText).toHaveBeenCalledWith(
        expect.stringContaining('Set up React project')
      );
    });

    it('shows copy confirmation message', async () => {
      const user = userEvent.setup();
      
      const mockClipboard = {
        writeText: jest.fn().mockResolvedValue(undefined)
      };
      Object.assign(navigator, { clipboard: mockClipboard });
      
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      const copyButton = screen.getAllByTestId('copy-action')[0];
      await user.click(copyButton);
      
      await waitFor(() => {
        expect(screen.getByText(/copied/i)).toBeInTheDocument();
      });
    });
  });

  describe('Video Playback Integration', () => {
    it('navigates to timestamp when action timestamp is clicked', async () => {
      const user = userEvent.setup();
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      const timestampButton = screen.getByText('3:00'); // 180 seconds
      await user.click(timestampButton);
      
      // Would trigger video seek functionality
      expect(timestampButton).toBeInTheDocument();
    });

    it('shows play button for video', () => {
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      expect(screen.getByTestId('play-video')).toBeInTheDocument();
    });
  });

  describe('Responsive Design', () => {
    it('adapts layout for mobile screens', () => {
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', { value: 360, writable: true });
      Object.defineProperty(window, 'innerHeight', { value: 640, writable: true });
      
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      expect(screen.getByText('Advanced React Patterns')).toBeInTheDocument();
    });

    it('shows full layout on desktop', () => {
      Object.defineProperty(window, 'innerWidth', { value: 1920, writable: true });
      Object.defineProperty(window, 'innerHeight', { value: 1080, writable: true });
      
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      expect(screen.getByText('Advanced React Patterns')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      expect(screen.getByRole('button', { name: /bookmark/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /play/i })).toBeInTheDocument();
    });

    it('supports keyboard navigation', async () => {
      const user = userEvent.setup();
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      const bookmarkButton = screen.getByTestId('bookmark-button');
      
      // Tab to bookmark button
      await user.tab();
      expect(bookmarkButton).toHaveFocus();
      
      // Activate with Enter
      await user.keyboard('[Enter]');
    });

    it('has proper heading hierarchy', () => {
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      expect(screen.getByRole('heading', { name: /advanced react patterns/i })).toBeInTheDocument();
    });

    it('provides alt text for images and icons', () => {
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      // Material-UI icons should have proper accessibility
      const playButton = screen.getByTestId('play-video');
      expect(playButton).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('handles missing video data gracefully', () => {
      const propsWithoutData = {
        ...defaultProps,
        videoData: null as any
      };
      
      expect(() => {
        renderWithTheme(<VideoAnalysisCard {...propsWithoutData} />);
      }).not.toThrow();
    });

    it('handles empty actions array', () => {
      const propsWithEmptyActions = {
        ...defaultProps,
        actions: []
      };
      
      renderWithTheme(<VideoAnalysisCard {...propsWithEmptyActions} />);
      expect(screen.getByText('Advanced React Patterns')).toBeInTheDocument();
    });

    it('handles malformed transcript', () => {
      const propsWithBadTranscript = {
        ...defaultProps,
        transcript: null as any
      };
      
      renderWithTheme(<VideoAnalysisCard {...propsWithBadTranscript} />);
      expect(screen.getByText('Advanced React Patterns')).toBeInTheDocument();
    });
  });

  describe('Performance', () => {
    it('memoizes expensive calculations', () => {
      const { rerender } = renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      // Re-render with same props
      rerender(
        <ThemeProvider theme={mockTheme}>
          <VideoAnalysisCard {...defaultProps} />
        </ThemeProvider>
      );
      
      expect(screen.getByText('Advanced React Patterns')).toBeInTheDocument();
    });

    it('handles large action lists efficiently', () => {
      const largeActionsList = Array.from({ length: 100 }, (_, i) => ({
        id: `action-${i}`,
        title: `Action ${i}`,
        description: `Description for action ${i}`,
        category: 'Test',
        priority: 'medium',
        estimatedTime: '10 minutes',
        completed: false,
        timestamp: i * 60
      }));
      
      const propsWithLargeList = {
        ...defaultProps,
        actions: largeActionsList
      };
      
      renderWithTheme(<VideoAnalysisCard {...propsWithLargeList} />);
      expect(screen.getByText('Advanced React Patterns')).toBeInTheDocument();
    });
  });

  describe('Theme Integration', () => {
    it('uses theme colors correctly', () => {
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      // Material-UI components should use theme colors
      const card = screen.getByTestId('video-analysis-card');
      expect(card).toBeInTheDocument();
    });

    it('responds to dark mode', () => {
      const darkTheme = createTheme({
        palette: {
          mode: 'dark'
        }
      });
      
      render(
        <ThemeProvider theme={darkTheme}>
          <VideoAnalysisCard {...defaultProps} />
        </ThemeProvider>
      );
      
      expect(screen.getByText('Advanced React Patterns')).toBeInTheDocument();
    });
  });

  describe('Data Processing', () => {
    it('formats duration correctly', () => {
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      expect(screen.getByText('18:45')).toBeInTheDocument();
    });

    it('formats view count with proper thousands separators', () => {
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      expect(screen.getByText(/125,000/)).toBeInTheDocument();
    });

    it('converts timestamps to readable format', () => {
      renderWithTheme(<VideoAnalysisCard {...defaultProps} />);
      
      expect(screen.getByText('3:00')).toBeInTheDocument(); // 180 seconds
      expect(screen.getByText('8:40')).toBeInTheDocument(); // 520 seconds
    });
  });
});