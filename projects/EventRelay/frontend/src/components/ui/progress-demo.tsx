import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardContent, CardTitle } from './card';
import {
  ProgressBar,
  EnhancedProgressBar,
  ProgressSteps,
  EnhancedProgressSteps,
  ProgressCircle,
  EnhancedProgressCircle,
  ProgressTimeline,
  EnhancedProgressTimeline,
  ProgressSpinner,
  EnhancedProgressSpinner,
  ProgressStatus,
  EnhancedProgressStatus,
  StatusGroup
} from './index';

export function ProgressDemo() {
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  // Simulate progress
  useEffect(() => {
    const timer = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(timer);
          return 100;
        }
        return prev + 10;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // Simulate step progression
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentStep(prev => {
        if (prev >= 4) {
          clearInterval(timer);
          return 4;
        }
        return prev + 1;
      });
    }, 2000);

    return () => clearInterval(timer);
  }, []);

  // Sample data for components
  const steps = [
    { id: '1', label: 'Upload', description: 'Upload video file', status: 'completed' as const },
    { id: '2', label: 'Process', description: 'Process video content', status: 'completed' as const },
    { id: '3', label: 'Analyze', description: 'Analyze video data', status: 'active' as const },
    { id: '4', label: 'Generate', description: 'Generate insights', status: 'pending' as const },
    { id: '5', label: 'Complete', description: 'Finish processing', status: 'pending' as const }
  ];

  const timelineEvents = [
    {
      id: '1',
      title: 'Video Upload Started',
      description: 'Beginning video upload process',
      timestamp: new Date(Date.now() - 10000),
      status: 'completed' as const,
      duration: 5000
    },
    {
      id: '2',
      title: 'Processing Video',
      description: 'Extracting video frames and audio',
      timestamp: new Date(Date.now() - 5000),
      status: 'completed' as const,
      duration: 8000
    },
    {
      id: '3',
      title: 'AI Analysis',
      description: 'Running AI models on video content',
      timestamp: new Date(),
      status: 'active' as const
    },
    {
      id: '4',
      title: 'Generate Report',
      description: 'Creating comprehensive analysis report',
      timestamp: new Date(Date.now() + 5000),
      status: 'pending' as const
    }
  ];

  const statuses = [
    { id: '1', status: 'completed' as const, text: 'Upload Complete' },
    { id: '2', status: 'processing' as const, text: 'Processing' },
    { id: '3', status: 'pending' as const, text: 'Analysis Pending' },
    { id: '4', status: 'warning' as const, text: 'Quality Check' }
  ];

  return (
    <div className="p-6 space-y-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Progress Components Demo</h1>
        <p className="text-gray-600">Interactive showcase of all progress tracking components</p>
      </div>

      {/* Progress Bars */}
      <Card>
        <CardHeader>
          <CardTitle>Progress Bars</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <h3 className="text-lg font-medium mb-3">Basic Progress Bar</h3>
            <ProgressBar
              currentStep={currentStep}
              totalSteps={5}
              status="processing"
              animated={true}
            />
          </div>

          <div>
            <h3 className="text-lg font-medium mb-3">Enhanced Progress Bar</h3>
            <EnhancedProgressBar
              currentStep={currentStep}
              totalSteps={5}
              status="processing"
              stepLabels={['Upload', 'Process', 'Analyze', 'Generate', 'Complete']}
              showETA={true}
              speed="normal"
            />
          </div>
        </CardContent>
      </Card>

      {/* Progress Steps */}
      <Card>
        <CardHeader>
          <CardTitle>Progress Steps</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <h3 className="text-lg font-medium mb-3">Basic Progress Steps</h3>
            <ProgressSteps
              steps={steps}
              currentStepIndex={currentStep}
              showStepDescriptions={true}
              animated={true}
            />
          </div>

          <div>
            <h3 className="text-lg font-medium mb-3">Enhanced Progress Steps</h3>
            <EnhancedProgressSteps
              steps={steps}
              currentStepIndex={currentStep}
              showProgressBar={true}
              showStepTiming={true}
            />
          </div>
        </CardContent>
      </Card>

      {/* Progress Circles */}
      <Card>
        <CardHeader>
          <CardTitle>Progress Circles</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <h3 className="text-lg font-medium mb-3">Basic Progress Circle</h3>
              <ProgressCircle
                progress={progress}
                status="processing"
                size={120}
              />
            </div>

            <div>
              <h3 className="text-lg font-medium mb-3">Enhanced Progress Circle</h3>
              <EnhancedProgressCircle
                progress={progress}
                status="processing"
                showProgressText={true}
                showStatusIcon={true}
                onProgressComplete={() => console.log('Progress complete!')}
              />
            </div>

            <div>
              <h3 className="text-lg font-medium mb-3">Multi-Size Progress Circle</h3>
              <div className="flex flex-col gap-4">
                <ProgressCircle progress={75} size={80} status="completed" />
                <ProgressCircle progress={50} size={100} status="processing" />
                <ProgressCircle progress={25} size={120} status="pending" />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Progress Timeline */}
      <Card>
        <CardHeader>
          <CardTitle>Progress Timeline</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <h3 className="text-lg font-medium mb-3">Basic Progress Timeline</h3>
            <ProgressTimeline
              events={timelineEvents}
              currentEventIndex={2}
              showTimestamps={true}
              showDurations={true}
              variant="detailed"
            />
          </div>

          <div>
            <h3 className="text-lg font-medium mb-3">Enhanced Progress Timeline</h3>
            <EnhancedProgressTimeline
              events={timelineEvents}
              currentEventIndex={2}
              showProgressBar={true}
              showEventCount={true}
              autoAdvance={false}
            />
          </div>
        </CardContent>
      </Card>

      {/* Progress Spinners */}
      <Card>
        <CardHeader>
          <CardTitle>Progress Spinners</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <h3 className="text-lg font-medium mb-3">Different Spinner Variants</h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <ProgressSpinner variant="default" size="lg" text="Default" showText={true} />
              <ProgressSpinner variant="dots" size="lg" text="Dots" showText={true} />
              <ProgressSpinner variant="bars" size="lg" text="Bars" showText={true} />
              <ProgressSpinner variant="pulse" size="lg" text="Pulse" showText={true} />
              <ProgressSpinner variant="ripple" size="lg" text="Ripple" showText={true} />
            </div>
          </div>

          <div>
            <h3 className="text-lg font-medium mb-3">Enhanced Progress Spinner</h3>
            <EnhancedProgressSpinner
              variant="default"
              size="xl"
              text="Processing..."
              showText={true}
              showProgress={true}
              progress={progress}
              showETA={true}
              estimatedTime={30}
            />
          </div>
        </CardContent>
      </Card>

      {/* Progress Status */}
      <Card>
        <CardHeader>
          <CardTitle>Progress Status</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <h3 className="text-lg font-medium mb-3">Status Variants</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <ProgressStatus status="pending" text="Pending" variant="default" />
              <ProgressStatus status="processing" text="Processing" variant="outline" />
              <ProgressStatus status="completed" text="Completed" variant="solid" />
              <ProgressStatus status="failed" text="Failed" variant="minimal" />
            </div>
          </div>

          <div>
            <h3 className="text-lg font-medium mb-3">Status Group</h3>
            <StatusGroup
              statuses={statuses}
              layout="horizontal"
            />
          </div>

          <div>
            <h3 className="text-lg font-medium mb-3">Enhanced Progress Status</h3>
            <EnhancedProgressStatus
              status="processing"
              text="Video Analysis"
              showProgress={true}
              progress={progress}
              showETA={true}
              estimatedTime={45}
              showDetails={true}
              details={
                <div className="text-sm">
                  <p>Current step: Frame extraction</p>
                  <p>Processed: 1,234 frames</p>
                  <p>Remaining: 567 frames</p>
                </div>
              }
            />
          </div>
        </CardContent>
      </Card>

      {/* Interactive Controls */}
      <Card>
        <CardHeader>
          <CardTitle>Interactive Controls</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsLoading(!isLoading)}
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors"
            >
              {isLoading ? 'Stop Loading' : 'Start Loading'}
            </button>
            
            <button
              onClick={() => setProgress(0)}
              className="px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 transition-colors"
            >
              Reset Progress
            </button>
            
            <button
              onClick={() => setCurrentStep(0)}
              className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 transition-colors"
            >
              Reset Steps
            </button>
          </div>

          <div className="text-sm text-gray-600">
            <p>• Progress automatically increases every second</p>
            <p>• Steps automatically advance every 2 seconds</p>
            <p>• Use buttons above to control the demo</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
