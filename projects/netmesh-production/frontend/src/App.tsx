import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { CircularProgress, Box } from '@mui/material';
import './styles/globals.css';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { ThemeProvider } from './theme/ThemeProvider';

// Lazy load heavy components for better performance
const Dashboard = lazy(() => import('./components/dashboard/Dashboard').then(module => ({ default: module.Dashboard })));
const MaterialDashboard = lazy(() => import('./components/dashboard/MaterialDashboard').then(module => ({ default: module.MaterialDashboard })));
const OperationsDashboard = lazy(() => import('./components/operations/OperationsDashboard').then(module => ({ default: module.OperationsDashboard })));
const LayoutIntegrationDemo = lazy(() => import('./components/layout/layout-integration-demo').then(module => ({ default: module.LayoutIntegrationDemo })));
const VideoAnalysisCard = lazy(() => import('./components/VideoAnalysisCard'));
const LearningFusion = lazy(() => import('./components/LearningFusion'));
const InteractiveLearningHub = lazy(() => import('./components/InteractiveLearningHub'));

// Loading fallback component
const LoadingFallback = () => (
  <Box
    sx={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh'
    }}
  >
    <CircularProgress size={60} />
  </Box>
);

function App() {
  return (
    <ThemeProvider>
      <ErrorBoundary>
        <Router>
          <div className="App">
            <Suspense fallback={<LoadingFallback />}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/deployments" element={<Dashboard />} />
                <Route path="/dashboard-legacy" element={<MaterialDashboard />} />
                <Route path="/layout-demo" element={<LayoutIntegrationDemo />} />
                <Route path="/video-analysis" element={<VideoAnalysisCard />} />
                <Route path="/learning-fusion" element={<LearningFusion />} />
                <Route path="/interactive-hub" element={<InteractiveLearningHub />} />
              </Routes>
            </Suspense>
          </div>
        </Router>
      </ErrorBoundary>
    </ThemeProvider>
  );
}

export default App;
