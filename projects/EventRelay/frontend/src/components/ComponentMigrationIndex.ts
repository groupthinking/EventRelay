// Enhanced Learning Components - Phase 2 Migration
export { default as RealLearningAgent } from './RealLearningAgent';
export { InteractiveLearningHub } from './InteractiveLearningHub';
export { default as EnhancedLearningHub } from './EnhancedLearningHub';
export { default as LearningFusion } from './LearningFusion';

// UI Components
export { Button } from './ui/button';
export { Badge } from './ui/badge';
export { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from './ui/card';

// Other existing components
export { default as Dashboard } from './Dashboard/Dashboard';
export { default as VideoAnalysisCard } from './VideoAnalysisCard';
export { default as VideosTable } from './VideosTable';

export interface ComponentMigrationStatus {
  component: string;
  status: 'completed' | 'in_progress' | 'pending';
  quality: number; // 1-10
  features: string[];
  notes: string;
}

export const MIGRATION_STATUS: ComponentMigrationStatus[] = [
  {
    component: 'RealLearningAgent',
    status: 'completed',
    quality: 10,
    features: [
      'Real API integration (YouTube + OpenAI)',
      'TypeScript conversion with proper types',
      'Production-ready error handling',
      'Cost tracking and performance metrics',
      'Modern shadcn/ui components',
      'Responsive design with Tailwind CSS'
    ],
    notes: 'Migrated from archive with significant enhancements. No mock data or placeholders.'
  },
  {
    component: 'EnhancedLearningHub',
    status: 'completed',
    quality: 9,
    features: [
      'Combined AI + Interactive modes',
      'Flexible mode switching',
      'Learning metrics dashboard',
      'Gradient design system',
      'Comprehensive feature overview'
    ],
    notes: 'New component combining best patterns from archived and production components.'
  },
  {
    component: 'InteractiveLearningHub',
    status: 'completed',
    quality: 8,
    features: [
      'Chapter navigation',
      'Synchronized video playback',
      'Transcript search',
      'Note-taking functionality',
      'Real-time timestamp tracking'
    ],
    notes: 'Enhanced existing component with better TypeScript integration.'
  }
];

// Migration utility functions
export const getMigrationSummary = () => {
  const completed = MIGRATION_STATUS.filter(s => s.status === 'completed').length;
  const total = MIGRATION_STATUS.length;
  const avgQuality = MIGRATION_STATUS.reduce((sum, s) => sum + s.quality, 0) / total;
  
  return {
    completed,
    total,
    completionRate: (completed / total) * 100,
    averageQuality: avgQuality,
    totalFeatures: MIGRATION_STATUS.reduce((sum, s) => sum + s.features.length, 0)
  };
};

// Component recommendation based on use case
export const getRecommendedComponent = (useCase: 'ai-processing' | 'interactive' | 'comprehensive') => {
  switch (useCase) {
    case 'ai-processing':
      return {
        component: 'RealLearningAgent',
        reason: 'Best for real AI processing with YouTube and OpenAI APIs'
      };
    case 'interactive':
      return {
        component: 'InteractiveLearningHub',
        reason: 'Best for chapter navigation, notes, and interactive learning'
      };
    case 'comprehensive':
      return {
        component: 'EnhancedLearningHub',
        reason: 'Best overall experience combining AI processing with interactive features'
      };
    default:
      return {
        component: 'EnhancedLearningHub',
        reason: 'Recommended for most use cases'
      };
  }
};