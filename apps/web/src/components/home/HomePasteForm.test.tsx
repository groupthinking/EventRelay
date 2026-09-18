/* @vitest-environment jsdom */
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import HomePasteForm from './HomePasteForm';

const mocks = vi.hoisted(() => ({
  push: vi.fn(),
  submitHomePaste: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mocks.push }),
}));

vi.mock('@/lib/studio-handoff', () => ({
  submitHomePaste: mocks.submitHomePaste,
}));

beforeEach(() => {
  mocks.push.mockReset();
  mocks.submitHomePaste.mockReset();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('HomePasteForm', () => {
  it('identifies an invalid YouTube URL and announces the existing error', () => {
    mocks.submitHomePaste.mockReturnValue(null);
    render(<HomePasteForm />);

    const input = screen.getByLabelText('YouTube URL');
    fireEvent.change(input, { target: { value: 'not a YouTube URL' } });
    fireEvent.submit(input.closest('form')!);

    expect(input.getAttribute('aria-invalid')).toBe('true');
    expect(input.getAttribute('aria-describedby')).toBe('home-youtube-url-error');
    const alert = screen.getByRole('alert');
    expect(alert.id).toBe('home-youtube-url-error');
    expect(alert.textContent).toBe('Need a valid YouTube URL.');
    expect(mocks.push).not.toHaveBeenCalled();
  });

  it('continues to the existing Studio handoff after valid input', () => {
    mocks.submitHomePaste.mockReturnValue('/studio?video=fixture');
    render(<HomePasteForm />);

    const input = screen.getByLabelText('YouTube URL');
    fireEvent.change(input, { target: { value: 'https://www.youtube.com/watch?v=auJzb1D-fag' } });
    fireEvent.submit(input.closest('form')!);

    expect(mocks.push).toHaveBeenCalledWith('/studio?video=fixture');
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
