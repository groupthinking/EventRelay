import { useState, useRef, useCallback } from 'react';
import './styles/App.css';
import { validateYoutubeUrl, analyzeVideo } from './lib/api';
import type { VideoAnalysis } from './lib/api';
import ThemeToggle from './components/ThemeToggle';
import HomeDashboard from './components/HomeDashboard';

type LoadingPhase =
  | 'idle'
  | 'validating'
  | 'fetching-transcript'
  | 'analyzing'
  | 'generating-insights'
  | 'complete'
  | 'error';

export default function App() {
  const [loadingPhase, setLoadingPhase] = useState<LoadingPhase>('idle');
  const [analysis, setAnalysis] = useState<VideoAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback(async (urlInput?: string) => {
    const url = urlInput || inputRef.current?.value.trim() || '';

    if (!url) {
      // In a real app, we'd open a modal here if triggered by FAB
      return;
    }

    // Reset state
    setError(null);
    setAnalysis(null);
    setLoadingPhase('validating');

    // Validate URL
    const validation = validateYoutubeUrl(url);
    if (!validation.isValid) {
      setError(validation.error || 'Invalid YouTube URL');
      setLoadingPhase('error');
      return;
    }

    setLoadingPhase('fetching-transcript');

    try {
      await new Promise(resolve => setTimeout(resolve, 500));
      setLoadingPhase('analyzing');

      const response = await analyzeVideo({
        youtube_url: url,
        action_type: 'full_analysis',
      });

      if (response.status === 'error') {
        setError(response.error || 'Analysis failed');
        setLoadingPhase('error');
        return;
      }

      setLoadingPhase('generating-insights');
      await new Promise(resolve => setTimeout(resolve, 300));

      setAnalysis(response.data || null);
      setLoadingPhase('complete');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
      setLoadingPhase('error');
    }
  }, []);

  const handleNewAnalysis = useCallback(() => {
    const url = prompt("Enter YouTube URL:");
    if (url) handleSubmit(url);
  }, [handleSubmit]);

  const isLoading = loadingPhase !== 'idle' && loadingPhase !== 'complete' && loadingPhase !== 'error';

  return (
    <div className="app">
      <HomeDashboard
        analysis={analysis}
        isLoading={isLoading}
        loadingPhase={loadingPhase}
        onNewAnalysis={handleNewAnalysis}
      />

      {/*
        Keep ThemeToggle for now, maybe integrate into Settings later
      */}
      <div style={{ position: 'fixed', top: '1rem', right: '1rem', zIndex: 100 }}>
        <ThemeToggle />
      </div>

      {error && (
        <div className="error-toast" style={{
          position: 'fixed',
          bottom: '8rem',
          left: '50%',
          transform: 'translateX(-50%)',
          backgroundColor: '#ef4444',
          color: 'white',
          padding: '0.75rem 1.5rem',
          borderRadius: '0.5rem',
          boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
          zIndex: 1000
        }}>
          {error}
          <button onClick={() => setError(null)} style={{ marginLeft: '1rem', background: 'none', border: 'none', color: 'white', fontWeight: 'bold' }}>×</button>
        </div>
      )}
    </div>
  );
}
