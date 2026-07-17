/**
 * SSE streaming endpoint for real-time agent pipeline visualization.
 */

import { analyzeVideoWithGemini, type VideoAnalysisResult } from '@/lib/gemini-video-analyzer';
import { hasGeminiKey } from '@/lib/gemini-client';
import { waitUntil } from '@vercel/functions';
import { publishEvent, EventTypes } from '@/lib/cloudevents';
import { backendHeaders, resolveBackendStatusUrl } from '@/lib/pipeline-backend';
import { checkBackendHealth, getBackendConfig } from '@/lib/pipeline-backend-health';
import { saveTrainingExample, TUNING_THRESHOLD } from '@/lib/training-store';
import { PipelineDeadline } from '../route';

const { configured: BACKEND_CONFIGURED, url: CONFIGURED_BACKEND_URL } = getBackendConfig();
const JOB_POLL_INTERVAL_MS = 2000;
const MAX_JOB_POLL_ATTEMPTS = 90;

export const runtime = 'nodejs';
export const maxDuration = 240;
