import { forwardRef } from 'react';
import './VideoInput.css';

interface VideoInputProps {
  onSubmit: () => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  isLoading: boolean;
  loadingPhase: string;
}

const VideoInput = forwardRef<HTMLInputElement, VideoInputProps>(
  ({ onSubmit, onKeyDown, isLoading, loadingPhase }, ref) => {
    const getButtonText = () => {
      switch (loadingPhase) {
        case 'validating':
          return 'Validating...';
        case 'fetching-transcript':
          return 'Fetching...';
        case 'analyzing':
          return 'Analyzing...';
        case 'generating-insights':
          return 'Generating...';
        default:
          return 'Analyze Video';
      }
    };

    return (
      <div className="video-input-container">
        <label htmlFor="youtube-url" className="input-label">
          Paste a YouTube URL
        </label>
        <div className="input-wrapper">
          <input
            ref={ref}
            id="youtube-url"
            type="url"
            className="video-input"
            placeholder="https://www.youtube.com/watch?v=..."
            disabled={isLoading}
            onKeyDown={onKeyDown}
            autoComplete="off"
          />
          <div className="input-icon">🔗</div>
        </div>
        <button
          className="analyze-button"
          onClick={onSubmit}
          disabled={isLoading}
        >
          {isLoading && <span className="spinner" />}
          {getButtonText()}
        </button>
      </div>
    );
  }
);

VideoInput.displayName = 'VideoInput';

export default VideoInput;
