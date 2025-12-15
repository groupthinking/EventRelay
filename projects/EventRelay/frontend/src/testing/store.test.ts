import { renderHook, act } from '@testing-library/react';
import { useAppStore } from '../store/appStore';

describe('App Store', () => {
  beforeEach(() => {
    // Clear store before each test
    const { result } = renderHook(() => useAppStore());
    act(() => {
      result.current.reset();
    });
  });

  test('initializes with default values', () => {
    const { result } = renderHook(() => useAppStore());
    
    expect(result.current.theme).toBe('light');
    expect(result.current.isSidebarCollapsed).toBe(false);
    expect(result.current.videos).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  test('toggles theme correctly', () => {
    const { result } = renderHook(() => useAppStore());
    
    act(() => {
      result.current.setTheme('dark');
    });
    
    expect(result.current.theme).toBe('dark');
    
    act(() => {
      result.current.setTheme('light');
    });
    
    expect(result.current.theme).toBe('light');
  });

  test('toggles sidebar collapse state', () => {
    const { result } = renderHook(() => useAppStore());
    
    act(() => {
      result.current.toggleSidebar();
    });
    
    expect(result.current.isSidebarCollapsed).toBe(true);
    
    act(() => {
      result.current.toggleSidebar();
    });
    
    expect(result.current.isSidebarCollapsed).toBe(false);
  });

  test('adds videos to store', () => {
    const { result } = renderHook(() => useAppStore());
    const testVideo = {
      id: 'test-1',
      title: 'Test Video',
      url: 'https://youtube.com/watch?v=test',
      thumbnail: 'test-thumbnail.jpg',
      duration: '10:00',
      views: '1000',
      uploadedAt: '2023-01-01',
      status: 'pending' as const
    };
    
    act(() => {
      result.current.addVideo(testVideo);
    });
    
    expect(result.current.videos).toHaveLength(1);
    expect(result.current.videos[0]).toEqual(testVideo);
  });

  test('removes videos from store', () => {
    const { result } = renderHook(() => useAppStore());
    const testVideo = {
      id: 'test-1',
      title: 'Test Video',
      url: 'https://youtube.com/watch?v=test',
      thumbnail: 'test-thumbnail.jpg',
      duration: '10:00',
      views: '1000',
      uploadedAt: '2023-01-01',
      status: 'pending' as const
    };
    
    act(() => {
      result.current.addVideo(testVideo);
    });
    
    expect(result.current.videos).toHaveLength(1);
    
    act(() => {
      result.current.removeVideo('test-1');
    });
    
    expect(result.current.videos).toHaveLength(0);
  });

  test('sets loading state', () => {
    const { result } = renderHook(() => useAppStore());
    
    act(() => {
      result.current.setLoading(true);
    });
    
    expect(result.current.isLoading).toBe(true);
    
    act(() => {
      result.current.setLoading(false);
    });
    
    expect(result.current.isLoading).toBe(false);
  });

  test('sets error state', () => {
    const { result } = renderHook(() => useAppStore());
    const testError = 'Test error message';
    
    act(() => {
      result.current.setError(testError);
    });
    
    expect(result.current.error).toBe(testError);
    
    act(() => {
      result.current.clearError();
    });
    
    expect(result.current.error).toBe(null);
  });

  test('resets store to initial state', () => {
    const { result } = renderHook(() => useAppStore());
    
    // Modify store state
    act(() => {
      result.current.setTheme('dark');
      result.current.toggleSidebar();
      result.current.addVideo({
        id: 'test-1',
        title: 'Test Video',
        url: 'https://youtube.com/watch?v=test',
        thumbnail: 'test-thumbnail.jpg',
        duration: '10:00',
        views: '1000',
        uploadedAt: '2023-01-01',
        status: 'pending' as const
      });
      result.current.setError('Test error');
    });
    
    // Reset store
    act(() => {
      result.current.reset();
    });
    
    expect(result.current.theme).toBe('light');
    expect(result.current.isSidebarCollapsed).toBe(false);
    expect(result.current.videos).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });
});
