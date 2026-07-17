import { describe, expect, it } from 'vitest';

import {
  isContactEmail,
  isYouTubeUrl,
  normalizeContactVideoUrl,
  validateContactForm,
} from '../contact-form-validation';

describe('normalizeContactVideoUrl', () => {
  it('returns empty string for blank input', () => {
    expect(normalizeContactVideoUrl('')).toBe('');
    expect(normalizeContactVideoUrl('   ')).toBe('');
  });

  it('prefixes https when scheme is missing', () => {
    expect(normalizeContactVideoUrl('youtube.com/watch?v=abc')).toBe(
      'https://youtube.com/watch?v=abc',
    );
  });

  it('preserves existing http(s) URLs', () => {
    expect(normalizeContactVideoUrl('https://youtu.be/abc')).toBe('https://youtu.be/abc');
  });
});

describe('isContactEmail', () => {
  it('accepts well-formed addresses', () => {
    expect(isContactEmail('you@company.com')).toBe(true);
  });

  it('rejects malformed addresses', () => {
    expect(isContactEmail('not-an-email')).toBe(false);
    expect(isContactEmail('@missing-local.com')).toBe(false);
  });
});

describe('isYouTubeUrl', () => {
  it('allows empty optional video URL', () => {
    expect(isYouTubeUrl('')).toBe(true);
  });

  it.each([
    'https://www.youtube.com/watch?v=abc',
    'https://youtu.be/abc',
    'https://m.youtube.com/watch?v=abc',
  ])('accepts YouTube host %s', (url) => {
    expect(isYouTubeUrl(url)).toBe(true);
  });

  it('rejects non-YouTube hosts', () => {
    expect(isYouTubeUrl('https://vimeo.com/123')).toBe(false);
  });
});

describe('validateContactForm', () => {
  it('requires name, email, use case, and message', () => {
    expect(
      validateContactForm({
        name: '',
        email: 'you@company.com',
        useCase: 'Engineering workflow',
        videoUrl: '',
        message: 'Need API docs from demos.',
      }),
    ).toEqual({
      ok: false,
      error: 'Please fill out name, email, use case, and the short note.',
    });
  });

  it('rejects overlong name or message', () => {
    expect(
      validateContactForm({
        name: 'a'.repeat(101),
        email: 'you@company.com',
        useCase: 'Engineering workflow',
        videoUrl: '',
        message: 'Short note.',
      }),
    ).toEqual({
      ok: false,
      error: 'Keep the name under 100 characters and the note under 1,000 characters.',
    });
  });

  it('rejects invalid email', () => {
    expect(
      validateContactForm({
        name: 'Ada',
        email: 'bad-email',
        useCase: 'Engineering workflow',
        videoUrl: '',
        message: 'Short note.',
      }),
    ).toEqual({ ok: false, error: 'Please enter a valid email address.' });
  });

  it('rejects non-YouTube sample URLs', () => {
    expect(
      validateContactForm({
        name: 'Ada',
        email: 'you@company.com',
        useCase: 'Engineering workflow',
        videoUrl: 'https://vimeo.com/123',
        message: 'Short note.',
      }),
    ).toEqual({
      ok: false,
      error: 'If you include a sample video, use a YouTube URL.',
    });
  });

  it('returns normalized mailto payload when valid', () => {
    const result = validateContactForm({
      name: ' Ada ',
      email: ' you@company.com ',
      useCase: 'Engineering workflow',
      videoUrl: 'youtu.be/abc',
      message: ' Turn demos into docs. ',
    });

    expect(result).toEqual({
      ok: true,
      mailto: {
        subject: 'UVAI inbound: Engineering workflow',
        body: [
          'Name: Ada',
          'Email: you@company.com',
          'Use case: Engineering workflow',
          'Sample video: https://youtu.be/abc',
          '',
          'Note:',
          'Turn demos into docs.',
        ].join('\n'),
      },
    });
  });
});