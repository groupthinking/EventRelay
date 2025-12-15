import React, { useEffect, useState } from 'react';
import { ApiService } from '../services/api';
import { ScoreBadge } from './ScoreBadge';

type Row = {
  video_id: string;
  title?: string;
  category?: string;
  actions?: number;
  score?: number;
  safety?: number;
  processed_at?: string;
};

export function VideosTable({ onSelect }: { onSelect: (id: string) => void }) {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        // Use real API to get processed videos
        const videos = await ApiService.getVideoList();
        const processedVideos = videos.map(video => ({
          video_id: video.id,
          title: video.analysis?.title || video.analysis?.metadata?.title || 'Untitled',
          category: video.analysis?.categorization?.primary_category || video.analysis?.category || 'Unknown',
          actions: video.analysis?.actions?.immediate_actions?.length || 0,
          score: video.analysis?.content_analysis?.technical_depth || 0,
          safety: video.analysis?.errors?.length || 0,
          processed_at: video.updatedAt || video.createdAt
        }));
        setRows(processedVideos);
        
        // Fallback to demo data if no real videos are available
        if (processedVideos.length === 0) {
          const fallbackData: Row[] = [
            {
              video_id: 'demo-ai-intro',
              title: 'AI Introduction - Demo Analysis',
              category: 'Education',
              actions: 12,
              score: 8,
              safety: 0,
              processed_at: new Date().toISOString()
            },
            {
              video_id: 'demo-ml-basics',
              title: 'Machine Learning Basics - Demo',
              category: 'Technology',
              actions: 18,
              score: 9,
              safety: 0,
              processed_at: new Date(Date.now() - 3600000).toISOString()
            }
          ];
          setRows(fallbackData);
        }
      } catch (e) {
        console.error('Failed to load videos from API:', e);
        
        // Show demo data with error indication
        const errorData: Row[] = [
          {
            video_id: 'error-demo-1',
            title: '⚠️ API Connection Error - Demo Data',
            category: 'System',
            actions: 0,
            score: 0,
            safety: 1,
            processed_at: new Date().toISOString()
          }
        ];
        setRows(errorData);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <div>Loading…</div>;

  return (
    <div style={{ padding: 16 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left', padding: 8 }}>Video</th>
            <th style={{ textAlign: 'left', padding: 8 }}>Category</th>
            <th style={{ textAlign: 'right', padding: 8 }}>Actions</th>
            <th style={{ textAlign: 'left', padding: 8 }}>Score</th>
            <th style={{ textAlign: 'right', padding: 8 }}>Safety</th>
            <th style={{ textAlign: 'left', padding: 8 }}>Processed</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.video_id} style={{ cursor: 'pointer', borderTop: '1px solid #333' }} onClick={() => onSelect(r.video_id)}>
              <td style={{ padding: 8 }}>{r.title || r.video_id}</td>
              <td style={{ padding: 8 }}>{r.category}</td>
              <td style={{ padding: 8, textAlign: 'right' }}>{r.actions ?? '-'}</td>
              <td style={{ padding: 8 }}><ScoreBadge score={r.score} /></td>
              <td style={{ padding: 8, textAlign: 'right' }}>{r.safety}</td>
              <td style={{ padding: 8 }}>{r.processed_at ? new Date(r.processed_at).toLocaleString() : '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


