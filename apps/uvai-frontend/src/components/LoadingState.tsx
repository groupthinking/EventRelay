import './LoadingState.css';

export type LoadingPhase =
  | 'idle'
  | 'validating'
  | 'fetching-transcript'
  | 'analyzing'
  | 'generating-insights'
  | 'complete'
  | 'error';

interface LoadingStateProps {
  phase: LoadingPhase;
}

interface PhaseInfo {
  label: string;
  description: string;
  icon: string;
  step: number;
}

const PHASE_INFO: Record<LoadingPhase, PhaseInfo> = {
  idle: {
    label: 'Ready',
    description: 'Enter a YouTube URL to begin analysis',
    icon: '🎬',
    step: 0,
  },
  validating: {
    label: 'Validating',
    description: 'Checking video URL and metadata...',
    icon: '🔍',
    step: 1,
  },
  'fetching-transcript': {
    label: 'Fetching Transcript',
    description: 'Extracting audio and generating transcript...',
    icon: '📝',
    step: 2,
  },
  analyzing: {
    label: 'Analyzing',
    description: 'AI is processing the video content...',
    icon: '🧠',
    step: 3,
  },
  'generating-insights': {
    label: 'Generating Insights',
    description: 'Creating actionable insights and summaries...',
    icon: '💡',
    step: 4,
  },
  complete: {
    label: 'Complete',
    description: 'Analysis finished successfully!',
    icon: '✅',
    step: 5,
  },
  error: {
    label: 'Error',
    description: 'Something went wrong',
    icon: '❌',
    step: -1,
  },
};

const TOTAL_STEPS = 5;

export default function LoadingState({ phase }: LoadingStateProps) {
  const info = PHASE_INFO[phase];
  const progress = info.step > 0 ? (info.step / TOTAL_STEPS) * 100 : 0;

  if (phase === 'idle' || phase === 'complete') {
    return null;
  }

  return (
    <div className={`loading-state ${phase === 'error' ? 'error' : ''}`}>
      <div className="loading-header">
        <span className="loading-icon animate-pulse">{info.icon}</span>
        <div className="loading-text">
          <span className="loading-label">{info.label}</span>
          <span className="loading-description">{info.description}</span>
        </div>
      </div>

      {phase !== 'error' && (
        <div className="loading-progress">
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="progress-text">
            Step {info.step} of {TOTAL_STEPS}
          </span>
        </div>
      )}

      <div className="loading-steps">
        {Object.entries(PHASE_INFO)
          .filter(([key]) => !['idle', 'complete', 'error'].includes(key))
          .map(([key, stepInfo]) => (
            <div
              key={key}
              className={`step-item ${
                stepInfo.step < info.step ? 'completed' :
                stepInfo.step === info.step ? 'active' :
                'pending'
              }`}
            >
              <span className="step-indicator">
                {stepInfo.step < info.step ? '✓' : stepInfo.step}
              </span>
              <span className="step-label">{stepInfo.label}</span>
            </div>
          ))
        }
      </div>
    </div>
  );
}
