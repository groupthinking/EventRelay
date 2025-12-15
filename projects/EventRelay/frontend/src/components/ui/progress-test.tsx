import React from 'react';
import {
  ProgressBar,
  ProgressSteps,
  ProgressCircle,
  ProgressTimeline,
  ProgressSpinner,
  ProgressStatus
} from './index';

export function ProgressTest() {
  // Test data
  const testSteps = [
    { id: '1', label: 'Test', description: 'Test step', status: 'completed' as const },
    { id: '2', label: 'Test 2', description: 'Test step 2', status: 'active' as const }
  ];

  const testEvents = [
    {
      id: '1',
      title: 'Test Event',
      description: 'Test event description',
      timestamp: new Date(),
      status: 'completed' as const
    }
  ];

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold">Progress Components Test</h2>
      
      <div>
        <h3 className="font-medium mb-2">Progress Bar</h3>
        <ProgressBar
          currentStep={1}
          totalSteps={2}
          status="processing"
        />
      </div>

      <div>
        <h3 className="font-medium mb-2">Progress Steps</h3>
        <ProgressSteps
          steps={testSteps}
          currentStepIndex={1}
        />
      </div>

      <div>
        <h3 className="font-medium mb-2">Progress Circle</h3>
        <ProgressCircle
          progress={50}
          status="processing"
          size={80}
        />
      </div>

      <div>
        <h3 className="font-medium mb-2">Progress Timeline</h3>
        <ProgressTimeline
          events={testEvents}
          currentEventIndex={0}
        />
      </div>

      <div>
        <h3 className="font-medium mb-2">Progress Spinner</h3>
        <ProgressSpinner
          variant="default"
          size="md"
          text="Loading..."
          showText={true}
        />
      </div>

      <div>
        <h3 className="font-medium mb-2">Progress Status</h3>
        <ProgressStatus
          status="processing"
          text="Processing..."
        />
      </div>

      <div className="text-green-600 text-sm">
        ✅ All components rendered successfully!
      </div>
    </div>
  );
}
