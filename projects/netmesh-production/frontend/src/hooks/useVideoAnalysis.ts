import { useState, useCallback, useRef, useEffect } from 'react';

// Enhanced video analysis interfaces
export interface VideoMetadata {
  id: string;
  title: string;
  description: string;
  duration: number;
  thumbnail: string;
  channel: string;
  publishedAt: string;
  viewCount: number;
  likeCount: number;
  tags: string[];
}

export interface AnalysisResult {
  summary: string;
  keyPoints: string[];
  topics: string[];
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  estimatedLearningTime: number; // in minutes
  prerequisites: string[];
  learningOutcomes: string[];
  codeExamples: string[];
  transcript: string;
  chapters: Chapter[];
  sentiment: 'positive' | 'neutral' | 'negative';
  qualityScore: number; // 1-10
}

export interface Chapter {
  id: string;
  title: string;
  startTime: number;
  endTime: number;
  summary: string;
  keyConcepts: string[];
}

export interface VideoAnalysisState {
  isLoading: boolean;
  error: string | null;
  data: AnalysisResult | null;
  progress: number;
  currentStep: string;
  metadata: VideoMetadata | null;
  isPaused: boolean;
  retryCount: number;
}

export interface AnalysisOptions {
  includeTranscript?: boolean;
  includeChapters?: boolean;
  includeCodeExtraction?: boolean;
  includeSentimentAnalysis?: boolean;
  qualityThreshold?: number;
  maxKeyPoints?: number;
}

export const useVideoAnalysis = (options: AnalysisOptions = {}) => {
  const [analysisState, setAnalysisState] = useState<VideoAnalysisState>({
    isLoading: false,
    error: null,
    data: null,
    progress: 0,
    currentStep: '',
    metadata: null,
    isPaused: false,
    retryCount: 0,
  });

  const abortControllerRef = useRef<AbortController | null>(null);
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Default options
  const defaultOptions: Required<AnalysisOptions> = {
    includeTranscript: true,
    includeChapters: true,
    includeCodeExtraction: true,
    includeSentimentAnalysis: true,
    qualityThreshold: 7,
    maxKeyPoints: 10,
    ...options,
  };

  // Update progress with smooth animation
  const updateProgress = useCallback((progress: number, step: string) => {
    setAnalysisState(prev => ({
      ...prev,
      progress: Math.min(progress, 100),
      currentStep: step,
    }));
  }, []);

  // Start progress simulation
  const startProgressSimulation = useCallback(() => {
    let currentProgress = 0;
    const steps = [
      { progress: 15, step: 'Fetching video metadata...' },
      { progress: 30, step: 'Analyzing video content...' },
      { progress: 50, step: 'Extracting transcript...' },
      { progress: 70, step: 'Generating chapters...' },
      { progress: 85, step: 'Analyzing sentiment...' },
      { progress: 95, step: 'Finalizing analysis...' },
      { progress: 100, step: 'Analysis complete!' },
    ];

    let stepIndex = 0;
    progressIntervalRef.current = setInterval(() => {
      if (stepIndex < steps.length) {
        const { progress, step } = steps[stepIndex];
        updateProgress(progress, step);
        stepIndex++;
      } else {
        if (progressIntervalRef.current) {
          clearInterval(progressIntervalRef.current);
        }
      }
    }, 800);
  }, [updateProgress]);

  // Analyze video with enhanced capabilities
  const analyzeVideo = useCallback(async (videoUrl: string, customOptions?: AnalysisOptions) => {
    // Cancel any ongoing analysis
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller
    abortControllerRef.current = new AbortController();

    // Reset state
    setAnalysisState(prev => ({
      ...prev,
      isLoading: true,
      error: null,
      data: null,
      progress: 0,
      currentStep: 'Initializing analysis...',
      isPaused: false,
    }));

    try {
      // Start progress simulation
      startProgressSimulation();

      // Merge options
      const finalOptions = { ...defaultOptions, ...customOptions };

      // Fetch video metadata first
      const metadataResponse = await fetch('http://localhost:8000/api/video/metadata', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ videoUrl }),
        signal: abortControllerRef.current.signal,
      });

      if (!metadataResponse.ok) {
        throw new Error('Failed to fetch video metadata');
      }

      const metadata: VideoMetadata = await metadataResponse.json();
      
      // Update state with metadata
      setAnalysisState(prev => ({
        ...prev,
        metadata,
        progress: 20,
        currentStep: 'Metadata retrieved, analyzing content...',
      }));

      // Perform full analysis
      const analysisResponse = await fetch('http://localhost:8000/api/video/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          videoUrl, 
          options: finalOptions,
          metadata 
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!analysisResponse.ok) {
        throw new Error('Failed to analyze video');
      }

      const result: AnalysisResult = await analysisResponse.json();

      // Clear progress interval
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }

      // Update final state
      setAnalysisState(prev => ({
        ...prev,
        isLoading: false,
        data: result,
        progress: 100,
        currentStep: 'Analysis complete!',
        error: null,
        retryCount: 0,
      }));

      return result;

    } catch (err: any) {
      // Clear progress interval
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }

      // Handle abort errors differently
      if (err.name === 'AbortError') {
        setAnalysisState(prev => ({
          ...prev,
          isLoading: false,
          currentStep: 'Analysis cancelled',
          progress: 0,
        }));
        return null;
      }

      // Handle other errors
      setAnalysisState(prev => ({
        ...prev,
        isLoading: false,
        error: err.message,
        progress: 0,
        currentStep: 'Analysis failed',
        retryCount: prev.retryCount + 1,
      }));

      throw err;
    }
  }, [defaultOptions, startProgressSimulation]);

  // Pause/resume analysis
  const togglePause = useCallback(() => {
    setAnalysisState(prev => ({
      ...prev,
      isPaused: !prev.isPaused,
    }));
  }, []);

  // Cancel analysis
  const cancelAnalysis = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
    }
    setAnalysisState(prev => ({
      ...prev,
      isLoading: false,
      isPaused: false,
      progress: 0,
      currentStep: 'Analysis cancelled',
    }));
  }, []);

  // Retry analysis
  const retryAnalysis = useCallback(() => {
    if (analysisState.metadata) {
      analyzeVideo(analysisState.metadata.id);
    }
  }, [analysisState.metadata, analyzeVideo]);

  // Get analysis insights
  const getInsights = useCallback(() => {
    if (!analysisState.data) return null;

    return {
      learningPath: analysisState.data.prerequisites.length > 0 
        ? `Prerequisites: ${analysisState.data.prerequisites.join(', ')}`
        : 'No prerequisites required',
      timeInvestment: `${analysisState.data.estimatedLearningTime} minutes`,
      difficulty: analysisState.data.difficulty,
      quality: `${analysisState.data.qualityScore}/10`,
      topics: analysisState.data.topics.slice(0, 5).join(', '),
    };
  }, [analysisState.data]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
    };
  }, []);

  return {
    ...analysisState,
    analyzeVideo,
    togglePause,
    cancelAnalysis,
    retryAnalysis,
    getInsights,
    isAborted: abortControllerRef.current?.signal.aborted || false,
  };
};
