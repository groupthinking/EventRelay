/**
 * Capability cards for the Home showcase. Descriptions only: nothing here is a
 * recorded result, a metric, or a sample output (REAL_MODE_ONLY).
 */
export const SHOWCASE_SAMPLE_URL = 'https://www.youtube.com/watch?v=auJzb1D-fag';

export const INTENTS = [
  { id: 'tasks', label: 'Extract tasks' },
  { id: 'sop', label: 'Build SOP' },
  { id: 'chapters', label: 'Clip chapters' },
  { id: 'workflow', label: 'Build workflow' },
  { id: 'ask', label: 'Ask' },
] as const;

export type IntentId = (typeof INTENTS)[number]['id'];

export const SHOWCASE_CATEGORIES = [
  'All',
  'Tutorials → Code',
  'Product demos',
  'Meetings → SOP',
  'Courses',
  'Workflows',
] as const;

export type ShowcaseCategory = Exclude<(typeof SHOWCASE_CATEGORIES)[number], 'All'>;

export type ShowcaseCard = {
  id: string;
  category: ShowcaseCategory;
  kind: 'Skill' | 'Feature';
  title: string;
  description: string;
  intent: IntentId;
  tone: 'accent' | 'success' | 'violet' | 'warn';
};

export const SHOWCASE_CARDS: readonly ShowcaseCard[] = [
  {
    id: 'tutorial-build-tasks',
    category: 'Tutorials → Code',
    kind: 'Skill',
    title: 'Tutorial to build tasks',
    description: 'Turn a coding tutorial into ordered, timestamped build tasks with proposed checks.',
    intent: 'tasks',
    tone: 'accent',
  },
  {
    id: 'tutorial-stack',
    category: 'Tutorials → Code',
    kind: 'Feature',
    title: 'Detected stack and starters',
    description: 'List the tools and frameworks named in the video and bind them to starter templates.',
    intent: 'tasks',
    tone: 'success',
  },
  {
    id: 'demo-features',
    category: 'Product demos',
    kind: 'Skill',
    title: 'Walkthrough to feature list',
    description: 'List the features and interactions shown on screen, each tied to a source timestamp.',
    intent: 'tasks',
    tone: 'violet',
  },
  {
    id: 'demo-checks',
    category: 'Product demos',
    kind: 'Feature',
    title: 'Proposed acceptance checks',
    description: 'Draft checks from what the demo claims. Checks stay proposed until they run.',
    intent: 'workflow',
    tone: 'warn',
  },
  {
    id: 'meeting-sop',
    category: 'Meetings → SOP',
    kind: 'Skill',
    title: 'Recording to SOP',
    description: 'Convert a recorded process walkthrough into step-by-step instructions with timestamps.',
    intent: 'sop',
    tone: 'accent',
  },
  {
    id: 'meeting-actions',
    category: 'Meetings → SOP',
    kind: 'Skill',
    title: 'Action items and open questions',
    description: 'Pull action items and unresolved questions out of a recorded discussion.',
    intent: 'tasks',
    tone: 'success',
  },
  {
    id: 'course-chapters',
    category: 'Courses',
    kind: 'Skill',
    title: 'Lecture to chapters',
    description: 'Split a lecture into numbered chapters with jump-to-timestamp links.',
    intent: 'chapters',
    tone: 'violet',
  },
  {
    id: 'course-ask',
    category: 'Courses',
    kind: 'Feature',
    title: 'Ask about a moment',
    description: 'Quote a transcript passage and ask a question grounded in that moment.',
    intent: 'ask',
    tone: 'accent',
  },
  {
    id: 'workflow-graph',
    category: 'Workflows',
    kind: 'Feature',
    title: 'Tasks and checks pipeline',
    description: 'Review extracted tasks and checks as one pipeline before anything is dispatched.',
    intent: 'workflow',
    tone: 'warn',
  },
  {
    id: 'workflow-export',
    category: 'Workflows',
    kind: 'Feature',
    title: 'Export the bound spec',
    description: 'Export the bound tasks and spec as Markdown for your own agent or editor.',
    intent: 'workflow',
    tone: 'success',
  },
];
