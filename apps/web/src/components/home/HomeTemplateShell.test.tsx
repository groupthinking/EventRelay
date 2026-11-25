/* @vitest-environment jsdom */
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import HomeTemplateShell from './HomeTemplateShell';

afterEach(cleanup);

describe('OpenAI template context disclosure', () => {
  it('keeps source input mounted while context opens and closes', () => {
    render(<HomeTemplateShell context={<p>Source evidence context</p>}>
      <label>Source URL<input defaultValue="retained-source" /></label>
    </HomeTemplateShell>);
    const input = screen.getByLabelText('Source URL') as HTMLInputElement;
    const toggle = screen.getByRole('button', { name: 'Show workflow details' });
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    const panel = document.getElementById(toggle.getAttribute('aria-controls')!);
    expect(panel?.classList.contains('is-open')).toBe(false);
    fireEvent.click(toggle);
    expect(toggle.getAttribute('aria-expanded')).toBe('true');
    expect(panel?.classList.contains('is-open')).toBe(true);
    expect(input.value).toBe('retained-source');
    fireEvent.click(screen.getByRole('button', { name: 'Hide workflow details' }));
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    expect(panel?.classList.contains('is-open')).toBe(false);
    expect(input.value).toBe('retained-source');
  });
});
