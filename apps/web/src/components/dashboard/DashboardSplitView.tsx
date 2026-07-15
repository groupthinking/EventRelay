'use client';

import type { Video } from '@/store/dashboard-types';
import DashboardCanvasView from './DashboardCanvasView';

export interface DashboardSplitViewProps {
  video: Video;
  onClose: () => void;
  onExtractEvents?: (videoId: string) => void;
}

/**
 * Per-video analysis workspace. Delegates to the video-canvas-centric layout
 * (large player center stage, time-synced transcript rail, and collapsible
 * insight/action/agent/search docks). Kept as a thin wrapper so existing
 * imports of `DashboardSplitView` continue to work unchanged.
 */
export default function DashboardSplitView({ video, onClose, onExtractEvents }: DashboardSplitViewProps) {
  return <DashboardCanvasView video={video} onClose={onClose} onExtractEvents={onExtractEvents} />;
}
