import { useState, useRef, useCallback } from 'react';
import './styles/App.css';
import { validateYoutubeUrl, getYoutubeEmbedUrl, analyzeVideo } from './lib/api';
import type { VideoAnalysis } from './lib/api';
import VideoInput from './components/VideoInput';
import VideoPreview from './components/VideoPreview';
import ContentTabs from './components/ContentTabs';
import ExampleGallery from './components/ExampleGallery';
import ThemeToggle from './components/ThemeToggle';
import LoadingState from './components/LoadingState';

type LoadingPhase =
  | 'idle'
  | 'validating'
  | 'fetching-transcript'
  | 'analyzing'
  | 'generating-insights'
  | 'complete'
  | 'error';

const EXAMPLE_VIDEOS = [
  {
    id: 'wa0MT8S_99E',
    url: 'https://www.youtube.com/watch?v=wa0MT8S_99E',
    title: 'Gemini 1.5 Pro: Video Intelligence',
    thumbnail: 'https://img.youtube.com/vi/wa0MT8S_99E/mqdefault.jpg',
  },
  {
    id: 'ScMzIvxBSi4',
    url: 'https://www.youtube.com/watch?v=ScMzIvxBSi4',
    title: 'Descript Product Walkthrough',
    thumbnail: 'https://img.youtube.com/vi/ScMzIvxBSi4/mqdefault.jpg',
  },
  {
    id: 'aircAruvnKk',
    url: 'https://www.youtube.com/watch?v=aircAruvnKk',
    title: 'Google I/O Keynote',
    thumbnail: 'https://img.youtube.com/vi/aircAruvnKk/mqdefault.jpg',
  },
];

export default function App() {
  const [videoUrl, setVideoUrl] = useState('');
  const [loadingPhase, setLoadingPhase] = useState<LoadingPhase>('idle');
  const [analysis, setAnalysis] = useState<VideoAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback(async () => {
    const url = inputRef.current?.value.trim() || '';

    if (!url) {
      inputRef.current?.focus();
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

    setVideoUrl(url);

    // Simulate loading phases for UX
    setLoadingPhase('fetching-transcript');

    try {
      // Small delay for phase transitions
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

  const handleExampleSelect = useCallback((url: string) => {
    if (inputRef.current) {
      inputRef.current.value = url;
    }
    setVideoUrl(url);
    handleSubmit();
  }, [handleSubmit]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && loadingPhase === 'idle') {
      handleSubmit();
    }
  }, [handleSubmit, loadingPhase]);

  const isLoading = loadingPhase !== 'idle' && loadingPhase !== 'complete' && loadingPhase !== 'error';

  return (
    <div className="app">
      <header className="header">
        <div className="header-brand">
          <span className="logo">✦</span>
          <span className="brand-name">UVAI</span>
        </div>
        <ThemeToggle />
      </header>

      <main className="main-container">
        <div className="left-panel">
          <div className="hero">
            <h1 className="headline">
              Transform Videos Into
              <span className="gradient-text"> Intelligence</span>
            </h1>
            <p className="subtitle">
              Paste any YouTube URL and unlock AI-powered insights, summaries, and actionable workflows.
            </p>
          </div>

          <VideoInput
            ref={inputRef}
            onSubmit={handleSubmit}
            onKeyDown={handleKeyDown}
            isLoading={isLoading}
            loadingPhase={loadingPhase}
          />

          <VideoPreview
            url={videoUrl}
            embedUrl={videoUrl ? getYoutubeEmbedUrl(videoUrl) : ''}
            isLoading={isLoading}
          />

          <div className="desktop-gallery">
            <ExampleGallery
              examples={EXAMPLE_VIDEOS}
              onSelect={handleExampleSelect}
            />
          </div>
        </div>

        <div className="right-panel">
          <div className="content-area">
            {loadingPhase === 'idle' && !analysis && (
              <div className="content-placeholder">
                <div className="placeholder-icon">✦</div>
                <p>Paste a YouTube URL or select an example to begin</p>
              </div>
            )}

            {isLoading && (
              <LoadingState phase={loadingPhase} />
            )}

            {loadingPhase === 'error' && error && (
              <div className="error-state">
                <div className="error-icon">⚠</div>
                <h3>Something went wrong</h3>
                <p>{error}</p>
                <button
                  className="btn btn-secondary"
                  onClick={() => setLoadingPhase('idle')}
                >
                  Try Again
                </button>
              </div>
            )}

            {loadingPhase === 'complete' && analysis && (
              <ContentTabs analysis={analysis} />
            )}
          </div>

          <div className="mobile-gallery">
            <ExampleGallery
              examples={EXAMPLE_VIDEOS}
              onSelect={handleExampleSelect}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
