import './VideoPreview.css';

interface VideoPreviewProps {
  url: string;
  embedUrl: string;
  isLoading: boolean;
}

export default function VideoPreview({ url, embedUrl, isLoading }: VideoPreviewProps) {
  return (
    <div className="video-preview-container">
      {url && embedUrl ? (
        <iframe
          className="video-iframe"
          src={embedUrl}
          title="YouTube video preview"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      ) : (
        <div className={`video-placeholder ${isLoading ? 'loading' : ''}`}>
          {isLoading ? (
            <div className="placeholder-loading">
              <div className="loading-pulse" />
            </div>
          ) : (
            <>
              <span className="placeholder-icon">▶</span>
              <span className="placeholder-text">Video preview will appear here</span>
            </>
          )}
        </div>
      )}
    </div>
  );
}
