import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface VideoData {
  id: string;
  title: string;
  url: string;
  thumbnail?: string;
  duration?: string;
  views?: string;
  uploadedAt?: string;
  analysis?: any;
  status: 'pending' | 'processing' | 'completed' | 'error';
}

interface AppState {
  // User preferences
  theme: 'light' | 'dark';
  isSidebarCollapsed: boolean;
  
  // Video data
  videos: VideoData[];
  currentVideo: VideoData | null;
  
  // UI state
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setTheme: (theme: 'light' | 'dark') => void;
  toggleSidebar: () => void;
  addVideo: (video: VideoData) => void;
  removeVideo: (id: string) => void;
  updateVideo: (id: string, updates: Partial<VideoData>) => void;
  setCurrentVideo: (video: VideoData | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
  reset: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Initial state
      theme: 'light',
      isSidebarCollapsed: false,
      videos: [],
      currentVideo: null,
      isLoading: false,
      error: null,
      
      // Actions
      setTheme: (theme) => set({ theme }),
      toggleSidebar: () => set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),
      
      addVideo: (video) => set((state) => ({ 
        videos: [...state.videos, video] 
      })),
      
      removeVideo: (id) => set((state) => ({
        videos: state.videos.filter(video => video.id !== id)
      })),
      
      updateVideo: (id, updates) => set((state) => ({
        videos: state.videos.map(video => 
          video.id === id ? { ...video, ...updates } : video
        )
      })),
      
      setCurrentVideo: (video) => set({ currentVideo: video }),
      setLoading: (loading) => set({ isLoading: loading }),
      setError: (error) => set({ error }),
      clearError: () => set({ error: null }),
      reset: () => set({
        theme: 'light',
        isSidebarCollapsed: false,
        videos: [],
        currentVideo: null,
        isLoading: false,
        error: null
      }),
    }),
    {
      name: 'youtube-extension-store',
      partialize: (state) => ({
        theme: state.theme,
        isSidebarCollapsed: state.isSidebarCollapsed,
        videos: state.videos,
      }),
    }
  )
);
