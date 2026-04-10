/**
 * Pre-built workflow templates for the UVAI Template Gallery.
 * Each template defines a named pipeline that users can launch with one click.
 */

export interface WorkflowTemplate {
  id: string;
  title: string;
  description: string;
  category: TemplateCategory;
  icon: string;
  gradient: string;
  stages: string[];
  estimatedTime: string;
  featured?: boolean;
  tags: string[];
}

export type TemplateCategory = 'engineering' | 'content' | 'research' | 'education' | 'business' | 'all';

export const CATEGORIES: { id: TemplateCategory; label: string; icon: string }[] = [
  { id: 'all', label: 'All Workflows', icon: '⚡' },
  { id: 'engineering', label: 'Engineering', icon: '🔧' },
  { id: 'content', label: 'Content', icon: '✍️' },
  { id: 'research', label: 'Research', icon: '🔬' },
  { id: 'education', label: 'Education', icon: '🎓' },
  { id: 'business', label: 'Business', icon: '📊' },
];

export const WORKFLOW_TEMPLATES: WorkflowTemplate[] = [
  {
    id: 'youtube-to-project',
    title: 'YouTube Tutorial → Deployable Project',
    description: 'Watches a coding tutorial, extracts every technology, framework, and code snippet, then generates a deployable project scaffold with working code.',
    category: 'engineering',
    icon: '🚀',
    gradient: 'from-emerald-500/20 to-cyan-500/20',
    stages: ['Download & Transcribe', 'Extract Technologies', 'Generate Scaffold', 'Deploy to Vercel'],
    estimatedTime: '2-5 min',
    featured: true,
    tags: ['code generation', 'deployment', 'scaffold'],
  },
  {
    id: 'conference-to-actions',
    title: 'Conference Talk → Action Items',
    description: 'Analyzes conference presentations and keynotes to extract key takeaways, action items, speaker insights, and generates a structured executive brief.',
    category: 'business',
    icon: '🎯',
    gradient: 'from-violet-500/20 to-fuchsia-500/20',
    stages: ['Transcribe Talk', 'Identify Key Themes', 'Extract Action Items', 'Generate Brief'],
    estimatedTime: '1-3 min',
    featured: true,
    tags: ['action items', 'executive brief', 'keynotes'],
  },
  {
    id: 'podcast-to-blog',
    title: 'Podcast → Blog Post',
    description: 'Transforms podcast episodes into SEO-optimized blog posts with proper formatting, pull quotes, timestamps, and social media snippets.',
    category: 'content',
    icon: '📝',
    gradient: 'from-amber-500/20 to-orange-500/20',
    stages: ['Transcribe Audio', 'Identify Structure', 'Generate Draft', 'SEO Optimization'],
    estimatedTime: '2-4 min',
    featured: true,
    tags: ['blog', 'SEO', 'content creation'],
  },
  {
    id: 'lecture-to-notes',
    title: 'Lecture → Study Notes + Flashcards',
    description: 'Converts educational lectures into comprehensive study notes with concept maps, key definitions, and spaced-repetition flashcards.',
    category: 'education',
    icon: '🎓',
    gradient: 'from-blue-500/20 to-indigo-500/20',
    stages: ['Transcribe Lecture', 'Extract Concepts', 'Generate Notes', 'Create Flashcards'],
    estimatedTime: '2-5 min',
    tags: ['study notes', 'flashcards', 'education'],
  },
  {
    id: 'demo-to-docs',
    title: 'Product Demo → API Documentation',
    description: 'Watches product demos and walkthroughs to generate structured API documentation, endpoint references, and integration guides.',
    category: 'engineering',
    icon: '📖',
    gradient: 'from-teal-500/20 to-green-500/20',
    stages: ['Analyze Demo', 'Map Endpoints', 'Generate Docs', 'Validate Examples'],
    estimatedTime: '3-6 min',
    tags: ['API docs', 'documentation', 'developer tools'],
  },
  {
    id: 'meeting-to-tasks',
    title: 'Meeting Recording → Task Board',
    description: 'Processes meeting recordings to extract decisions, assign action items to speakers, estimate effort, and push tasks to your project board.',
    category: 'business',
    icon: '📋',
    gradient: 'from-rose-500/20 to-pink-500/20',
    stages: ['Diarize Speakers', 'Extract Decisions', 'Assign Tasks', 'Export to Board'],
    estimatedTime: '1-3 min',
    tags: ['meetings', 'task management', 'productivity'],
  },
  {
    id: 'research-synthesis',
    title: 'Research Videos → Literature Review',
    description: 'Analyzes multiple research presentation videos, cross-references findings, identifies consensus and contradictions, and generates a synthesis report.',
    category: 'research',
    icon: '🔬',
    gradient: 'from-cyan-500/20 to-blue-500/20',
    stages: ['Batch Transcribe', 'Extract Claims', 'Cross-Reference', 'Synthesize Report'],
    estimatedTime: '5-10 min',
    tags: ['research', 'literature review', 'synthesis'],
  },
  {
    id: 'tutorial-to-course',
    title: 'Tutorial Series → Structured Course',
    description: 'Takes a playlist of tutorial videos and organizes them into a structured course with modules, prerequisites, quizzes, and a learning path.',
    category: 'education',
    icon: '🏫',
    gradient: 'from-purple-500/20 to-violet-500/20',
    stages: ['Analyze Playlist', 'Map Dependencies', 'Structure Modules', 'Generate Curriculum'],
    estimatedTime: '5-15 min',
    tags: ['course creation', 'curriculum', 'learning path'],
  },
  {
    id: 'competitor-intel',
    title: 'Competitor Videos → Intel Report',
    description: 'Monitors competitor product launches, demos, and announcements to generate competitive intelligence reports with feature comparisons.',
    category: 'business',
    icon: '🕵️',
    gradient: 'from-red-500/20 to-orange-500/20',
    stages: ['Scan Videos', 'Extract Features', 'Compare Products', 'Generate Intel'],
    estimatedTime: '3-8 min',
    tags: ['competitive intelligence', 'market research', 'analysis'],
  },
];
