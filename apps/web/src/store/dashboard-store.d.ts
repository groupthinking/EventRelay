/**
 * Centralized Zustand store for the EventRelay dashboard.
 *
 * Combines video processing, event extraction, and agent dispatch
 * into a single store so every component shares the same state.
 */
import type { ExtractedEvent, AgentExecution } from '@/lib/types';
export interface PipelineResult {
    live_url: string | null;
    github_repo: string | null;
    build_status: string;
    code_generation: {
        framework: string;
        files_created: string[];
        entry_point: string;
    } | null;
    deployment: {
        status: string;
        platforms: string[];
        urls: Record<string, string>;
    } | null;
}
export interface Video {
    id: string;
    title: string;
    url: string;
    status: 'processing' | 'complete' | 'failed';
    progress: number;
    thumbnail?: string;
    duration?: string;
    processedAt?: string;
    transcript?: string;
    events?: ExtractedEvent[];
    agents?: AgentExecution[];
    pipelineResult?: PipelineResult;
    insights?: {
        summary: string;
        actions: string[];
        sentiment: string;
        topics: string[];
    };
}
export interface Activity {
    time: string;
    event: string;
    type: 'success' | 'info' | 'error';
}
interface DashboardState {
    videos: Video[];
    activities: Activity[];
    selectedVideoId: string | null;
    loading: boolean;
    selectedVideo: () => Video | undefined;
    addVideo: (video: Video) => void;
    updateVideo: (id: string, patch: Partial<Video>) => void;
    removeVideo: (id: string) => void;
    selectVideo: (id: string | null) => void;
    addActivity: (event: string, type: Activity['type']) => void;
    setLoading: (loading: boolean) => void;
    processVideo: (url: string) => Promise<void>;
    deployPipeline: (url: string) => Promise<void>;
    extractEvents: (videoId: string) => void;
    dispatchAgents: (videoId: string) => void;
}
export declare const useDashboardStore: import("zustand").UseBoundStore<import("zustand").StoreApi<DashboardState>>;
export {};
