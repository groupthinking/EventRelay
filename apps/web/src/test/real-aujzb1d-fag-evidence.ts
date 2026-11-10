import type { GroundedSpecCandidate } from '@/lib/grounded-build-spec';

/** Read-only evidence captured from the current public pack for auJzb1D-fag. */
export const REAL_AUJ_VIDEO_ID = 'auJzb1D-fag' as const;
export const REAL_AUJ_SOURCE_URL = 'https://www.youtube.com/watch?v=auJzb1D-fag' as const;
export const REAL_AUJ_SOURCE_HASH =
  '2778c5fc08a1b7f19fe0a83bca959e24ecf20040c3cc1a3b6edd244d68c5e4ea' as const;
export const REAL_AUJ_EXTRACT_PIPELINE = 'p1.6-direct-shard-v1' as const;
export const REAL_AUJ_CONTENT_HASH =
  'e86e5b3383a64cc4508b4d5681a4c3e6e3aafe0c64473cf796e88cb8c82ea40c' as const;

export const REAL_AUJ_GROUNDED_SPEC: GroundedSpecCandidate = {
  version: '1',
  outputClass: 'browser-interactive',
  sourceStatus: 'full',
  confidence: 0.98,
  limitations: [
    'Live webcam/audio streaming and external Gemini API key executions require server/cloud backend services outside local browser sandbox.',
    'YouTube video fetching is simulated via local mock data unless connected to active Google AI Studio session.',
  ],
  app: {
    name: 'Google AI Studio Multimodal Playground Explorer',
    purpose: 'Interactive browser tool mimicking Google AI Studio multimodal workflows: video long-context prompt analysis and image spatial bounding box detection.',
  },
  screens: [
    { id: 'scr_chat_prompt', name: 'Chat Prompt Studio', purpose: 'Attach video URLs, configure Gemini model settings, and execute long-context summary prompts.' },
    { id: 'scr_spatial_build', name: 'Spatial Understanding Demo', purpose: 'Preview object detection with interactive 2D bounding boxes and inspect prototype React code.' },
  ],
  state: [
    { id: 'st_attached_media', name: 'Attached Media Item', description: 'Metadata and token count of the attached YouTube video or image source.', persistence: 'memory' },
    { id: 'st_prompt_query', name: 'Prompt Query Text', description: 'User instruction given to the model for multimodal analysis.', persistence: 'memory' },
    { id: 'st_analysis_output', name: 'Analysis Output', description: 'Generated structured summary with timestamps or detected 2D bounding boxes.', persistence: 'memory' },
  ],
  requirements: [
    {
      id: 'G-REQ-01', screenId: 'scr_chat_prompt', title: 'Video URL Attachment and Token Display',
      detail: 'Users can paste a YouTube video URL, save it into the prompt session, and display the calculated token count (~415,928 tokens).',
      classification: 'observed', required: true, capabilities: ['browser-ui', 'local-state'], rationale: 'Directly demonstrated in video when inserting YouTube video into prompt.',
      citations: [
        { kind: 'transcript', index: 30, videoId: REAL_AUJ_VIDEO_ID, startSeconds: 344, endSeconds: 353, quote: "So let's click the plus icon in the chat prompt interface, and this is coming from YouTube. So let's click that YouTube video, paste the video URL here, and click Save." },
        { kind: 'visual', index: 5, videoId: REAL_AUJ_VIDEO_ID, startSeconds: 360, endSeconds: 360, quote: 'Chat prompt with embedded video tokenized to 415,928 tokens and text query requesting summary' },
      ],
    },
    {
      id: 'G-REQ-02', screenId: 'scr_chat_prompt', title: 'Detailed Video Summary Generation',
      detail: 'The interface displays a structured summary containing Introduction timestamps, Core Benefits, Specifications, Demo user journeys, and Call to Action.',
      classification: 'observed', required: true, capabilities: ['browser-ui', 'local-state'], rationale: 'Model response shown in Google AI Studio after running prompt.',
      citations: [
        { kind: 'transcript', index: 33, videoId: REAL_AUJ_VIDEO_ID, startSeconds: 379, endSeconds: 395, quote: 'Okay wow, just as instructed, the model provided a detailed summary, very detailed, with main points, evidence, and some conclusions. This output is structured very nicely as well.' },
        { kind: 'visual', index: 6, videoId: REAL_AUJ_VIDEO_ID, startSeconds: 400, endSeconds: 400, quote: 'Structured video summary showing introduction timestamps (0:00 - 0:46 Introduction), Core Benefits, Specifications, Demo user journeys, and Call to Action' },
      ],
    },
    {
      id: 'G-REQ-03', screenId: 'scr_spatial_build', title: '2D Bounding Box Visualizer',
      detail: "Display uploaded image with overlaid 2D bounding boxes and labels when '2D bounding boxes' option is selected and prompt is sent.",
      classification: 'observed', required: true, capabilities: ['browser-ui', 'local-state'], rationale: 'Shown in the Spatial Understanding prototype demo inside the Build tab.',
      citations: [
        { kind: 'transcript', index: 38, videoId: REAL_AUJ_VIDEO_ID, startSeconds: 438, endSeconds: 454, quote: "When we send this to the model, we can see that it's added 2D bounding boxes and labeled what each item is. And if we click the code icon, we can see the behind the scenes code for what's actually making this work." },
        { kind: 'visual', index: 8, videoId: REAL_AUJ_VIDEO_ID, startSeconds: 455, endSeconds: 455, quote: 'Spatial Understanding web app preview with bounding box toggle controls, image preview with origami cats, and TSX source editor' },
      ],
    },
  ],
  acceptanceCriteria: [
    { id: 'AC-01', requirementId: 'G-REQ-01', given: 'User is on the Chat Prompt Studio screen', when: 'User clicks the add media button and selects YouTube Video with a valid URL', then: 'A video thumbnail badge appears in the input with token count ~415,928 tokens' },
    { id: 'AC-02', requirementId: 'G-REQ-02', given: 'A video is attached and prompt requesting detailed summary is run', when: 'Inference finishes', then: 'Structured sections with timestamps (e.g. 0:00 - 0:46 Introduction) are rendered' },
    { id: 'AC-03', requirementId: 'G-REQ-03', given: 'User is on the Spatial Understanding Demo screen', when: "User clicks '2D bounding boxes' and sends the request", then: 'Origami objects in the window frame image are highlighted with labeled colored bounding boxes' },
  ],
  unresolved: [
    { id: 'UNRES-01', requirementIds: ['G-REQ-01', 'G-REQ-02'], question: 'What is the token cost pricing tier when ingesting over 1M tokens in Gemini 2.5 Pro Preview?', required: false },
  ],
  unsupported: [
    { id: 'UNSUPP-01', requirementIds: ['G-REQ-01'], capability: 'server', reason: 'Direct live YouTube audio/video frame extraction requires Google AI Studio backend ingestion servers.', required: true },
  ],
};

export const REAL_AUJ_TRANSCRIPT_ROWS = [
  { idx: 30, start_s: 344, end_s: 353, text: "So let's click the plus icon in the chat prompt interface, and this is coming from YouTube. So let's click that YouTube video, paste the video URL here, and click Save." },
  { idx: 33, start_s: 379, end_s: 395, text: 'Okay wow, just as instructed, the model provided a detailed summary, very detailed, with main points, evidence, and some conclusions. This output is structured very nicely as well.' },
  { idx: 38, start_s: 438, end_s: 454, text: "When we send this to the model, we can see that it's added 2D bounding boxes and labeled what each item is. And if we click the code icon, we can see the behind the scenes code for what's actually making this work." },
];

export const REAL_AUJ_VISUAL_ROWS = [
  { timestamp: 360, element_type: 'ui_prompt', content: 'Chat prompt with embedded video tokenized to 415,928 tokens and text query requesting summary' },
  { timestamp: 400, element_type: 'ui_response', content: 'Structured video summary showing introduction timestamps (0:00 - 0:46 Introduction), Core Benefits, Specifications, Demo user journeys, and Call to Action' },
  { timestamp: 455, element_type: 'ui_demo', content: 'Spatial Understanding web app preview with bounding box toggle controls, image preview with origami cats, and TSX source editor' },
];
