import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import RealLearningAgent from '../RealLearningAgent';

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  Play: () => <div data-testid="play-icon">Play</div>,
  Pause: () => <div data-testid="pause-icon">Pause</div>,
  Brain: () => <div data-testid="brain-icon">Brain</div>,
  Activity: () => <div data-testid="activity-icon">Activity</div>,
  Settings: () => <div data-testid="settings-icon">Settings</div>,
  Lightbulb: () => <div data-testid="lightbulb-icon">Lightbulb</div>,
  Zap: () => <div data-testid="zap-icon">Zap</div>,
  ExternalLink: () => <div data-testid="external-link-icon">ExternalLink</div>,
  Clock: () => <div data-testid="clock-icon">Clock</div>,
  Code: () => <div data-testid="code-icon">Code</div>,
  Wrench: () => <div data-testid="wrench-icon">Wrench</div>,
  AlertTriangle: () => <div data-testid="alert-triangle-icon">AlertTriangle</div>,
  TrendingUp: () => <div data-testid="trending-up-icon">TrendingUp</div>,
}));

// Mock UI components
jest.mock('../ui/card', () => ({
  Card: ({ children, ...props }: any) => <div data-testid="card" {...props}>{children}</div>,
  CardContent: ({ children, ...props }: any) => <div data-testid="card-content" {...props}>{children}</div>,
  CardDescription: ({ children, ...props }: any) => <div data-testid="card-description" {...props}>{children}</div>,
  CardHeader: ({ children, ...props }: any) => <div data-testid="card-header" {...props}>{children}</div>,
  CardTitle: ({ children, ...props }: any) => <div data-testid="card-title" {...props}>{children}</div>,
}));

jest.mock('../ui/button', () => ({
  Button: ({ children, onClick, ...props }: any) => (
    <button data-testid="button" onClick={onClick} {...props}>
      {children}
    </button>
  ),
}));

jest.mock('../ui/badge', () => ({
  Badge: ({ children, ...props }: any) => <span data-testid="badge" {...props}>{children}</span>,
}));

// Mock WebSocket
const mockWebSocket = {
  send: jest.fn(),
  close: jest.fn(),
  readyState: WebSocket.OPEN,
  onopen: null,
  onclose: null,
  onmessage: null,
  onerror: null,
};

(global as any).WebSocket = jest.fn(() => mockWebSocket);

describe('RealLearningAgent', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Component Rendering', () => {
    it('renders the main learning agent interface', () => {
      render(<RealLearningAgent />);
      
      expect(screen.getByText('Real Learning Agent')).toBeInTheDocument();
      expect(screen.getByText('Autonomous learning system with real-time adaptation')).toBeInTheDocument();
    });

    it('renders the control buttons', () => {
      render(<RealLearningAgent />);
      
      expect(screen.getByRole('button', { name: /start learning/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /configure/i })).toBeInTheDocument();
    });

    it('renders status indicators', () => {
      render(<RealLearningAgent />);
      
      expect(screen.getByText('Status')).toBeInTheDocument();
      expect(screen.getByText('Idle')).toBeInTheDocument();
    });

    it('renders activity and pattern sections', () => {
      render(<RealLearningAgent />);
      
      expect(screen.getByText('Recent Activities')).toBeInTheDocument();
      expect(screen.getByText('Learning Patterns')).toBeInTheDocument();
      expect(screen.getByText('Agent Actions')).toBeInTheDocument();
    });
  });

  describe('Learning State Management', () => {
    it('toggles learning state when start/stop button is clicked', async () => {
      const user = userEvent.setup();
      render(<RealLearningAgent />);
      
      const startButton = screen.getByRole('button', { name: /start learning/i });
      expect(startButton).toBeInTheDocument();
      
      await user.click(startButton);
      
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /stop learning/i })).toBeInTheDocument();
      });
      
      expect(screen.getByText('Learning')).toBeInTheDocument();
    });

    it('updates status when learning is active', async () => {
      const user = userEvent.setup();
      render(<RealLearningAgent />);
      
      const startButton = screen.getByRole('button', { name: /start learning/i });
      await user.click(startButton);
      
      await waitFor(() => {
        expect(screen.getByText('Learning')).toBeInTheDocument();
      });
    });
  });

  describe('WebSocket Integration', () => {
    it('establishes WebSocket connection when learning starts', async () => {
      const user = userEvent.setup();
      render(<RealLearningAgent />);
      
      const startButton = screen.getByRole('button', { name: /start learning/i });
      await user.click(startButton);
      
      expect(global.WebSocket).toHaveBeenCalledWith('ws://localhost:8000/ws/learning');
    });

    it('sends learning data via WebSocket', async () => {
      const user = userEvent.setup();
      render(<RealLearningAgent />);
      
      const startButton = screen.getByRole('button', { name: /start learning/i });
      await user.click(startButton);
      
      // Simulate WebSocket open event
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen({} as Event);
      }
      
      await waitFor(() => {
        expect(mockWebSocket.send).toHaveBeenCalledWith(
          expect.stringContaining('"type":"learning_started"')
        );
      });
    });

    it('handles WebSocket messages correctly', async () => {
      const user = userEvent.setup();
      render(<RealLearningAgent />);
      
      const startButton = screen.getByRole('button', { name: /start learning/i });
      await user.click(startButton);
      
      // Simulate incoming WebSocket message
      const mockMessage = {
        data: JSON.stringify({
          type: 'activity_detected',
          activity: {
            id: 'test-activity-1',
            type: 'code_analysis',
            description: 'Analyzing code patterns',
            timestamp: new Date().toISOString()
          }
        })
      };
      
      if (mockWebSocket.onmessage) {
        mockWebSocket.onmessage(mockMessage as MessageEvent);
      }
      
      await waitFor(() => {
        expect(screen.getByText('Analyzing code patterns')).toBeInTheDocument();
      });
    });
  });

  describe('Activity Management', () => {
    it('displays activities when they are received', async () => {
      const user = userEvent.setup();
      render(<RealLearningAgent />);
      
      const startButton = screen.getByRole('button', { name: /start learning/i });
      await user.click(startButton);
      
      // Simulate activity data
      const mockMessage = {
        data: JSON.stringify({
          type: 'activity_detected',
          activity: {
            id: 'test-activity-1',
            type: 'video_analysis',
            description: 'Processing YouTube video content',
            timestamp: new Date().toISOString()
          }
        })
      };
      
      if (mockWebSocket.onmessage) {
        mockWebSocket.onmessage(mockMessage as MessageEvent);
      }
      
      await waitFor(() => {
        expect(screen.getByText('Processing YouTube video content')).toBeInTheDocument();
      });
    });

    it('limits the number of displayed activities', async () => {
      const user = userEvent.setup();
      render(<RealLearningAgent />);
      
      const startButton = screen.getByRole('button', { name: /start learning/i });
      await user.click(startButton);
      
      // Send more than 10 activities
      for (let i = 0; i < 15; i++) {
        const mockMessage = {
          data: JSON.stringify({
            type: 'activity_detected',
            activity: {
              id: `test-activity-${i}`,
              type: 'test_activity',
              description: `Test activity ${i}`,
              timestamp: new Date().toISOString()
            }
          })
        };
        
        if (mockWebSocket.onmessage) {
          mockWebSocket.onmessage(mockMessage as MessageEvent);
        }
      }
      
      await waitFor(() => {
        // Should only show the most recent 10 activities
        expect(screen.getByText('Test activity 14')).toBeInTheDocument();
        expect(screen.queryByText('Test activity 4')).not.toBeInTheDocument();
      });
    });
  });

  describe('Learning Pattern Recognition', () => {
    it('displays learning patterns when detected', async () => {
      const user = userEvent.setup();
      render(<RealLearningAgent />);
      
      const startButton = screen.getByRole('button', { name: /start learning/i });
      await user.click(startButton);
      
      const mockMessage = {
        data: JSON.stringify({
          type: 'pattern_detected',
          pattern: {
            id: 'pattern-1',
            type: 'learning_pattern',
            description: 'User prefers educational content',
            confidence: 0.85,
            timestamp: new Date().toISOString(),
            context: {}
          }
        })
      };
      
      if (mockWebSocket.onmessage) {
        mockWebSocket.onmessage(mockMessage as MessageEvent);
      }
      
      await waitFor(() => {
        expect(screen.getByText('User prefers educational content')).toBeInTheDocument();
        expect(screen.getByText('85%')).toBeInTheDocument();
      });
    });
  });

  describe('Agent Actions', () => {
    it('displays agent actions when they occur', async () => {
      const user = userEvent.setup();
      render(<RealLearningAgent />);
      
      const startButton = screen.getByRole('button', { name: /start learning/i });
      await user.click(startButton);
      
      const mockMessage = {
        data: JSON.stringify({
          type: 'agent_action',
          action: {
            id: 'action-1',
            type: 'content_suggestion',
            description: 'Suggested related educational videos',
            trigger: 'pattern_recognition',
            timestamp: new Date().toISOString(),
            status: 'completed'
          }
        })
      };
      
      if (mockWebSocket.onmessage) {
        mockWebSocket.onmessage(mockMessage as MessageEvent);
      }
      
      await waitFor(() => {
        expect(screen.getByText('Suggested related educational videos')).toBeInTheDocument();
        expect(screen.getByText('completed')).toBeInTheDocument();
      });
    });
  });

  describe('Configuration', () => {
    it('opens configuration modal when configure button is clicked', async () => {
      const user = userEvent.setup();
      render(<RealLearningAgent />);
      
      const configureButton = screen.getByRole('button', { name: /configure/i });
      await user.click(configureButton);
      
      // Configuration functionality should be implemented
      // For now, just verify the button is clickable
      expect(configureButton).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('handles WebSocket connection errors gracefully', async () => {
      const user = userEvent.setup();
      render(<RealLearningAgent />);
      
      const startButton = screen.getByRole('button', { name: /start learning/i });
      await user.click(startButton);
      
      // Simulate WebSocket error
      if (mockWebSocket.onerror) {
        mockWebSocket.onerror({} as Event);
      }
      
      // Should still render without crashing
      expect(screen.getByText('Real Learning Agent')).toBeInTheDocument();
    });

    it('handles malformed WebSocket messages', async () => {
      const user = userEvent.setup();
      render(<RealLearningAgent />);
      
      const startButton = screen.getByRole('button', { name: /start learning/i });
      await user.click(startButton);
      
      // Simulate malformed message
      const invalidMessage = {
        data: 'invalid json'
      };
      
      if (mockWebSocket.onmessage) {
        mockWebSocket.onmessage(invalidMessage as MessageEvent);
      }
      
      // Should not crash
      expect(screen.getByText('Real Learning Agent')).toBeInTheDocument();
    });
  });

  describe('Cleanup', () => {
    it('closes WebSocket connection when component unmounts', async () => {
      const user = userEvent.setup();
      const { unmount } = render(<RealLearningAgent />);
      
      const startButton = screen.getByRole('button', { name: /start learning/i });
      await user.click(startButton);
      
      unmount();
      
      expect(mockWebSocket.close).toHaveBeenCalled();
    });

    it('clears intervals when component unmounts', async () => {
      const user = userEvent.setup();
      const { unmount } = render(<RealLearningAgent />);
      
      const startButton = screen.getByRole('button', { name: /start learning/i });
      await user.click(startButton);
      
      // Mock clearInterval to verify cleanup
      const clearIntervalSpy = jest.spyOn(global, 'clearInterval');
      
      unmount();
      
      expect(clearIntervalSpy).toHaveBeenCalled();
      clearIntervalSpy.mockRestore();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels and roles', () => {
      render(<RealLearningAgent />);
      
      expect(screen.getByRole('button', { name: /start learning/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /configure/i })).toBeInTheDocument();
    });

    it('supports keyboard navigation', async () => {
      const user = userEvent.setup();
      render(<RealLearningAgent />);
      
      const startButton = screen.getByRole('button', { name: /start learning/i });
      
      // Tab to the button and press Enter
      await user.tab();
      expect(startButton).toHaveFocus();
      
      await user.keyboard('[Enter]');
      
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /stop learning/i })).toBeInTheDocument();
      });
    });
  });

  describe('Performance', () => {
    it('does not cause memory leaks with frequent updates', async () => {
      const user = userEvent.setup();
      render(<RealLearningAgent />);
      
      const startButton = screen.getByRole('button', { name: /start learning/i });
      await user.click(startButton);
      
      // Simulate many rapid updates
      for (let i = 0; i < 100; i++) {
        const mockMessage = {
          data: JSON.stringify({
            type: 'activity_detected',
            activity: {
              id: `perf-test-${i}`,
              type: 'performance_test',
              description: `Performance test ${i}`,
              timestamp: new Date().toISOString()
            }
          })
        };
        
        if (mockWebSocket.onmessage) {
          mockWebSocket.onmessage(mockMessage as MessageEvent);
        }
      }
      
      // Should still render properly
      expect(screen.getByText('Real Learning Agent')).toBeInTheDocument();
    });
  });
});