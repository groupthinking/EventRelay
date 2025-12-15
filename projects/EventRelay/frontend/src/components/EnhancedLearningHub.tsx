import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import RealLearningAgent from './RealLearningAgent';
import { InteractiveLearningHub } from './InteractiveLearningHub';
import { 
  Brain, 
  Zap, 
  Settings, 
  Monitor,
  BookOpen,
  TrendingUp,
  Target,
  Activity
} from 'lucide-react';

interface EnhancedLearningHubProps {
  videoId?: string;
  videoUrl?: string;
  mode?: 'ai-agent' | 'interactive' | 'combined';
}

const EnhancedLearningHub: React.FC<EnhancedLearningHubProps> = ({
  videoId = '',
  videoUrl = '',
  mode = 'combined'
}) => {
  const [activeMode, setActiveMode] = useState<'ai-agent' | 'interactive' | 'combined'>(mode);
  const [learningMetrics, setLearningMetrics] = useState({
    videosProcessed: 0,
    totalLearningTime: 0,
    implementationsCreated: 0,
    conceptsMastered: 0
  });

  // Demo data for InteractiveLearningHub
  const demoVideoData = {
    title: 'Advanced React Patterns and Best Practices',
    channel: 'Tech Education Hub',
    duration: '18:45'
  };

  const demoChapters = [
    { id: '1', title: 'Introduction to Patterns', time: '0:00', timeSeconds: 0, duration: '3:15' },
    { id: '2', title: 'Component Composition', time: '3:15', timeSeconds: 195, duration: '5:30' },
    { id: '3', title: 'State Management Patterns', time: '8:45', timeSeconds: 525, duration: '6:00' },
    { id: '4', title: 'Performance Optimization', time: '14:45', timeSeconds: 885, duration: '4:00' }
  ];

  const demoTranscript = [
    { id: '1', start: 0, end: 15, text: 'Welcome to advanced React patterns. Today we\'ll explore component composition.', speaker: 'Instructor' },
    { id: '2', start: 15, end: 30, text: 'First, let\'s understand the compound component pattern and its benefits.', speaker: 'Instructor' },
    { id: '3', start: 30, end: 45, text: 'This pattern allows for flexible and reusable component APIs.', speaker: 'Instructor' }
  ];

  const renderModeContent = () => {
    switch (activeMode) {
      case 'ai-agent':
        return <RealLearningAgent />;
      case 'interactive':
        return (
          <InteractiveLearningHub
            videoId={videoId || 'jNQXAC9IVRw'}
            videoData={demoVideoData}
            chapters={demoChapters}
            transcript={demoTranscript}
          />
        );
      case 'combined':
        return (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <Card className="xl:col-span-1">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="w-5 h-5 text-purple-600" />
                  AI Processing Engine
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[600px] overflow-hidden">
                  <RealLearningAgent />
                </div>
              </CardContent>
            </Card>
            
            <Card className="xl:col-span-1">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-blue-600" />
                  Interactive Learning
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[600px] overflow-hidden">
                  <InteractiveLearningHub
                    videoId={videoId || 'jNQXAC9IVRw'}
                    videoData={demoVideoData}
                    chapters={demoChapters}
                    transcript={demoTranscript}
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        );
      default:
        return <div>Invalid mode selected</div>;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <Card className="border-2 border-gradient-to-r from-blue-500 to-purple-600">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                  <Zap className="w-6 h-6 text-white" />
                </div>
                <div>
                  <CardTitle className="text-2xl text-gray-900">Enhanced Learning Hub</CardTitle>
                  <p className="text-gray-600">AI-Powered Video-to-Action Intelligence Platform</p>
                </div>
              </div>
              
              {/* Learning Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">{learningMetrics.videosProcessed}</div>
                  <div className="text-xs text-gray-500">Videos Processed</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">{learningMetrics.implementationsCreated}</div>
                  <div className="text-xs text-gray-500">Implementations</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">{learningMetrics.conceptsMastered}</div>
                  <div className="text-xs text-gray-500">Concepts Mastered</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-orange-600">{Math.floor(learningMetrics.totalLearningTime / 60)}</div>
                  <div className="text-xs text-gray-500">Hours Learned</div>
                </div>
              </div>
            </div>
          </CardHeader>
        </Card>

        {/* Mode Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Learning Mode Selection
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              <Button
                variant={activeMode === 'ai-agent' ? 'default' : 'outline'}
                onClick={() => setActiveMode('ai-agent')}
                className="flex items-center gap-2"
              >
                <Brain className="w-4 h-4" />
                AI Processing Agent
                <Badge variant="secondary" className="ml-2">10/10 Quality</Badge>
              </Button>
              
              <Button
                variant={activeMode === 'interactive' ? 'default' : 'outline'}
                onClick={() => setActiveMode('interactive')}
                className="flex items-center gap-2"
              >
                <Monitor className="w-4 h-4" />
                Interactive Learning
                <Badge variant="outline" className="ml-2">Enhanced</Badge>
              </Button>
              
              <Button
                variant={activeMode === 'combined' ? 'default' : 'outline'}
                onClick={() => setActiveMode('combined')}
                className="flex items-center gap-2"
              >
                <Target className="w-4 h-4" />
                Combined Mode
                <Badge variant="default" className="ml-2 bg-gradient-to-r from-blue-500 to-purple-600">Recommended</Badge>
              </Button>
            </div>

            {/* Mode Descriptions */}
            <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
                <div className="flex items-center gap-2 mb-2">
                  <Brain className="w-4 h-4 text-purple-600" />
                  <h4 className="font-semibold text-purple-800">AI Processing Agent</h4>
                </div>
                <p className="text-sm text-purple-700">
                  Real API integration with YouTube and OpenAI. Processes videos with actual AI analysis, 
                  cost tracking, and implementation-focused outputs.
                </p>
                <div className="mt-2">
                  <Badge variant="secondary" className="text-xs">Production Ready</Badge>
                </div>
              </div>

              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex items-center gap-2 mb-2">
                  <Monitor className="w-4 h-4 text-blue-600" />
                  <h4 className="font-semibold text-blue-800">Interactive Learning</h4>
                </div>
                <p className="text-sm text-blue-700">
                  Chapter-based navigation, transcript search, note-taking, and synchronized video playback 
                  for enhanced learning experience.
                </p>
                <div className="mt-2">
                  <Badge variant="outline" className="text-xs">Feature Rich</Badge>
                </div>
              </div>

              <div className="p-4 bg-gradient-to-br from-blue-50 to-purple-50 rounded-lg border border-gradient-to-r from-blue-200 to-purple-200">
                <div className="flex items-center gap-2 mb-2">
                  <Target className="w-4 h-4 text-gradient-to-r from-blue-600 to-purple-600" />
                  <h4 className="font-semibold bg-gradient-to-r from-blue-800 to-purple-800 bg-clip-text text-transparent">Combined Mode</h4>
                </div>
                <p className="text-sm text-gray-700">
                  Best of both worlds - AI processing power with interactive learning features. 
                  Ideal for comprehensive video-to-action workflows.
                </p>
                <div className="mt-2">
                  <Badge className="text-xs bg-gradient-to-r from-blue-500 to-purple-600">Ultimate Experience</Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Dynamic Content */}
        {renderModeContent()}

        {/* Features Summary */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Enhanced Features Activated
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
                <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
                  <Brain className="w-4 h-4 text-white" />
                </div>
                <div>
                  <div className="font-semibold text-green-800">Real AI Processing</div>
                  <div className="text-xs text-green-600">YouTube + OpenAI APIs</div>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
                <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                  <TrendingUp className="w-4 h-4 text-white" />
                </div>
                <div>
                  <div className="font-semibold text-blue-800">Performance Metrics</div>
                  <div className="text-xs text-blue-600">Cost & Time Tracking</div>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 bg-purple-50 rounded-lg">
                <div className="w-8 h-8 bg-purple-500 rounded-full flex items-center justify-center">
                  <Target className="w-4 h-4 text-white" />
                </div>
                <div>
                  <div className="font-semibold text-purple-800">Action-Oriented</div>
                  <div className="text-xs text-purple-600">Implementation Focus</div>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 bg-orange-50 rounded-lg">
                <div className="w-8 h-8 bg-orange-500 rounded-full flex items-center justify-center">
                  <BookOpen className="w-4 h-4 text-white" />
                </div>
                <div>
                  <div className="font-semibold text-orange-800">Interactive UI</div>
                  <div className="text-xs text-orange-600">Notes & Navigation</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default EnhancedLearningHub;