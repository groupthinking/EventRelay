import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ErrorBoundary } from '../components/common/ErrorBoundary';

// Mock child component that throws an error
const ThrowError = () => {
  throw new Error('Test error for error boundary');
};

// Mock child component that doesn't throw
const NormalComponent = () => <div>Normal component</div>;

describe('ErrorBoundary Component', () => {
  beforeEach(() => {
    // Suppress console.error for expected errors in tests
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('renders children when no error occurs', () => {
    render(
      <ErrorBoundary>
        <NormalComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('Normal component')).toBeInTheDocument();
  });

  test('renders error UI when error occurs', () => {
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });
});
