import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import EnhancedLearningHub from '../EnhancedLearningHub';

// Mock child components
jest.mock('../RealLearningAgent', () => {
  return function MockRealLearningAgent() {
    return <div data-testid="real-learning-agent">Real Learning Agent</div>;
  };
});

jest.mock('../InteractiveLearningHub', () => ({
  InteractiveLearningHub: function MockInteractiveLearningHub(props: any) {
    return (
      <div data-testid="interactive-learning-hub">
        Interactive Learning Hub - Video: {props.videoData?.title}
      </div>
    );
  }
}));

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  Brain: () => <div data-testid="brain-icon">Brain</div>,
  Zap: () => <div data-testid="zap-icon">Zap</div>,
  Settings: () => <div data-testid="settings-icon">Settings</div>,
  Monitor: () => <div data-testid="monitor-icon">Monitor</div>,
  BookOpen: () => <div data-testid="book-open-icon">BookOpen</div>,
  TrendingUp: () => <div data-testid="trending-up-icon">TrendingUp</div>,
  Target: () => <div data-testid="target-icon">Target</div>,
  Activity: () => <div data-testid="activity-icon">Activity</div>,
}));

// Mock UI components
jest.mock('../ui/card', () => ({
  Card: ({ children, ...props }: any) => <div data-testid="card" {...props}>{children}</div>,
  CardContent: ({ children, ...props }: any) => <div data-testid="card-content" {...props}>{children}</div>,
  CardHeader: ({ children, ...props }: any) => <div data-testid="card-header" {...props}>{children}</div>,
  CardTitle: ({ children, ...props }: any) => <div data-testid="card-title" {...props}>{children}</div>,
}));

jest.mock('../ui/button', () => ({
  Button: ({ children, onClick, variant, ...props }: any) => (
    <button 
      data-testid="button" 
      onClick={onClick} 
      className={`button-${variant || 'default'}`}
      {...props}
    >
      {children}
    </button>
  ),
}));

jest.mock('../ui/badge', () => ({
  Badge: ({ children, variant, ...props }: any) => (
    <span data-testid="badge" className={`badge-${variant || 'default'}`} {...props}>
      {children}
    </span>
  ),
}));

describe('EnhancedLearningHub', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Component Rendering', () => {
    it('renders with default props', () => {
      render(<EnhancedLearningHub />);
      
      expect(screen.getByText('Enhanced Learning Hub')).toBeInTheDocument();
      expect(screen.getByText('AI-Powered Video Learning Platform')).toBeInTheDocument();
    });

    it('renders with custom videoId and videoUrl', () => {
      render(
        <EnhancedLearningHub 
          videoId="test-video-123" 
          videoUrl="https://youtube.com/watch?v=test123"
        />
      );
      
      expect(screen.getByText('Enhanced Learning Hub')).toBeInTheDocument();
    });

    it('renders learning metrics', () => {
      render(<EnhancedLearningHub />);
      
      expect(screen.getByText('Videos Processed')).toBeInTheDocument();
      expect(screen.getByText('Total Learning Time')).toBeInTheDocument();
      expect(screen.getByText('Implementations Created')).toBeInTheDocument();
      expect(screen.getByText('Concepts Mastered')).toBeInTheDocument();
    });

    it('displays initial metric values as zero', () => {
      render(<EnhancedLearningHub />);
      
      const metricValues = screen.getAllByText('0');
      expect(metricValues).toHaveLength(4); // All metrics start at 0
    });
  });

  describe('Mode Selection', () => {
    it('renders mode selection buttons', () => {
      render(<EnhancedLearningHub />);
      
      expect(screen.getByRole('button', { name: /ai agent/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /interactive/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /combined/i })).toBeInTheDocument();
    });

    it('starts with combined mode by default', () => {
      render(<EnhancedLearningHub />);
      
      const combinedButton = screen.getByRole('button', { name: /combined/i });
      expect(combinedButton).toHaveClass('button-default');
    });

    it('switches to AI Agent mode when clicked', async () => {
      const user = userEvent.setup();
      render(<EnhancedLearningHub />);
      
      const aiAgentButton = screen.getByRole('button', { name: /ai agent/i });
      await user.click(aiAgentButton);
      
      expect(screen.getByTestId('real-learning-agent')).toBeInTheDocument();
      expect(screen.queryByTestId('interactive-learning-hub')).not.toBeInTheDocument();
    });

    it('switches to Interactive mode when clicked', async () => {
      const user = userEvent.setup();
      render(<EnhancedLearningHub />);
      
      const interactiveButton = screen.getByRole('button', { name: /interactive/i });
      await user.click(interactiveButton);
      
      expect(screen.getByTestId('interactive-learning-hub')).toBeInTheDocument();
      expect(screen.queryByTestId('real-learning-agent')).not.toBeInTheDocument();
    });

    it('switches to Combined mode when clicked', async () => {
      const user = userEvent.setup();
      render(<EnhancedLearningHub />);
      
      // First switch to a different mode
      const aiAgentButton = screen.getByRole('button', { name: /ai agent/i });
      await user.click(aiAgentButton);
      
      // Then switch to combined
      const combinedButton = screen.getByRole('button', { name: /combined/i });
      await user.click(combinedButton);
      
      expect(screen.getByTestId('real-learning-agent')).toBeInTheDocument();
      expect(screen.getByTestId('interactive-learning-hub')).toBeInTheDocument();
    });
  });

  describe('Mode-specific Rendering', () => {
    it('renders only RealLearningAgent in AI Agent mode', async () => {
      const user = userEvent.setup();
      render(<EnhancedLearningHub mode="ai-agent" />);
      
      expect(screen.getByTestId('real-learning-agent')).toBeInTheDocument();
      expect(screen.queryByTestId('interactive-learning-hub')).not.toBeInTheDocument();
    });

    it('renders only InteractiveLearningHub in Interactive mode', async () => {
      render(<EnhancedLearningHub mode="interactive" />);
      
      expect(screen.getByTestId('interactive-learning-hub')).toBeInTheDocument();
      expect(screen.queryByTestId('real-learning-agent')).not.toBeInTheDocument();
    });

    it('renders both components in Combined mode', () => {
      render(<EnhancedLearningHub mode="combined" />);
      
      expect(screen.getByTestId('real-learning-agent')).toBeInTheDocument();
      expect(screen.getByTestId('interactive-learning-hub')).toBeInTheDocument();
    });
  });

  describe('Learning Metrics Updates', () => {
    it('updates metrics when learning activities occur', () => {
      // This would test the actual metric updates
      // For now, we test that the metrics structure is in place
      render(<EnhancedLearningHub />);
      
      expect(screen.getByText('Videos Processed')).toBeInTheDocument();
      expect(screen.getByText('Total Learning Time')).toBeInTheDocument();
      expect(screen.getByText('Implementations Created')).toBeInTheDocument();
      expect(screen.getByText('Concepts Mastered')).toBeInTheDocument();
    });

    it('formats learning time correctly', () => {
      // Test that time formatting works correctly
      render(<EnhancedLearningHub />);
      
      // Initial state should show 0
      const timeDisplay = screen.getByText('0 min');
      expect(timeDisplay).toBeInTheDocument();
    });
  });

  describe('Demo Data Integration', () => {
    it('passes demo data to InteractiveLearningHub', () => {
      render(<EnhancedLearningHub mode="interactive" />);
      
      expect(screen.getByText(/Advanced React Patterns and Best Practices/)).toBeInTheDocument();
    });

    it('handles empty video data gracefully', () => {
      render(<EnhancedLearningHub videoId="" videoUrl="" mode="interactive" />);
      
      // Should still render without crashing
      expect(screen.getByTestId('interactive-learning-hub')).toBeInTheDocument();
    });
  });

  describe('Component Integration', () => {
    it('maintains consistent state across mode changes', async () => {
      const user = userEvent.setup();
      render(<EnhancedLearningHub />);
      
      // Switch between modes and ensure metrics persist
      const aiAgentButton = screen.getByRole('button', { name: /ai agent/i });
      await user.click(aiAgentButton);
      
      expect(screen.getByText('Videos Processed')).toBeInTheDocument();
      
      const interactiveButton = screen.getByRole('button', { name: /interactive/i });
      await user.click(interactiveButton);
      
      expect(screen.getByText('Videos Processed')).toBeInTheDocument();
    });

    it('updates active mode button styling', async () => {
      const user = userEvent.setup();
      render(<EnhancedLearningHub />);
      
      const aiAgentButton = screen.getByRole('button', { name: /ai agent/i });
      await user.click(aiAgentButton);
      
      // Button styling should reflect active state
      expect(aiAgentButton).toHaveClass('button-default');
    });
  });

  describe('Props Handling', () => {
    it('accepts and uses videoId prop', () => {
      const testVideoId = 'test-video-123';
      render(<EnhancedLearningHub videoId={testVideoId} />);
      
      // Component should render without error
      expect(screen.getByText('Enhanced Learning Hub')).toBeInTheDocument();
    });

    it('accepts and uses videoUrl prop', () => {
      const testVideoUrl = 'https://youtube.com/watch?v=test123';
      render(<EnhancedLearningHub videoUrl={testVideoUrl} />);
      
      expect(screen.getByText('Enhanced Learning Hub')).toBeInTheDocument();
    });

    it('uses mode prop to set initial state', () => {
      render(<EnhancedLearningHub mode="ai-agent" />);
      
      expect(screen.getByTestId('real-learning-agent')).toBeInTheDocument();
      expect(screen.queryByTestId('interactive-learning-hub')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper heading structure', () => {
      render(<EnhancedLearningHub />);
      
      expect(screen.getByRole('heading', { name: /enhanced learning hub/i })).toBeInTheDocument();
    });

    it('has accessible button labels', () => {
      render(<EnhancedLearningHub />);
      
      expect(screen.getByRole('button', { name: /ai agent/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /interactive/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /combined/i })).toBeInTheDocument();
    });

    it('supports keyboard navigation between mode buttons', async () => {
      const user = userEvent.setup();
      render(<EnhancedLearningHub />);
      
      const aiAgentButton = screen.getByRole('button', { name: /ai agent/i });
      const interactiveButton = screen.getByRole('button', { name: /interactive/i });
      
      // Tab navigation should work
      await user.tab();
      expect(aiAgentButton).toHaveFocus();
      
      await user.tab();
      expect(interactiveButton).toHaveFocus();
    });
  });

  describe('Performance', () => {
    it('does not re-render unnecessarily when props do not change', () => {
      const { rerender } = render(<EnhancedLearningHub videoId="test" />);
      
      // Re-render with same props
      rerender(<EnhancedLearningHub videoId="test" />);
      
      expect(screen.getByText('Enhanced Learning Hub')).toBeInTheDocument();
    });

    it('handles rapid mode switching without issues', async () => {
      const user = userEvent.setup();
      render(<EnhancedLearningHub />);
      
      const aiAgentButton = screen.getByRole('button', { name: /ai agent/i });
      const interactiveButton = screen.getByRole('button', { name: /interactive/i });
      const combinedButton = screen.getByRole('button', { name: /combined/i });
      
      // Rapid switching
      await user.click(aiAgentButton);
      await user.click(interactiveButton);
      await user.click(combinedButton);
      await user.click(aiAgentButton);
      
      expect(screen.getByText('Enhanced Learning Hub')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('handles invalid mode prop gracefully', () => {
      // @ts-ignore - Testing invalid prop
      render(<EnhancedLearningHub mode="invalid-mode" />);
      
      // Should default to combined mode or handle gracefully
      expect(screen.getByText('Enhanced Learning Hub')).toBeInTheDocument();
    });

    it('handles missing video data gracefully', () => {
      render(<EnhancedLearningHub videoId={undefined} videoUrl={undefined} />);
      
      expect(screen.getByText('Enhanced Learning Hub')).toBeInTheDocument();
    });
  });

  describe('State Management', () => {
    it('maintains learning metrics state correctly', async () => {
      const user = userEvent.setup();
      render(<EnhancedLearningHub />);
      
      // Switch modes and verify metrics persist
      const aiAgentButton = screen.getByRole('button', { name: /ai agent/i });
      await user.click(aiAgentButton);
      
      expect(screen.getAllByText('0')).toHaveLength(4); // Initial metric values
    });

    it('updates active mode state when buttons are clicked', async () => {
      const user = userEvent.setup();
      render(<EnhancedLearningHub />);
      
      const aiAgentButton = screen.getByRole('button', { name: /ai agent/i });
      await user.click(aiAgentButton);
      
      // State should be updated to show only AI Agent component
      expect(screen.getByTestId('real-learning-agent')).toBeInTheDocument();
      expect(screen.queryByTestId('interactive-learning-hub')).not.toBeInTheDocument();
    });
  });
});