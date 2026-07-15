export const CONTACT_NAME_MAX = 100;
export const CONTACT_MESSAGE_MAX = 1000;

const YOUTUBE_HOSTS = new Set([
  'youtube.com',
  'www.youtube.com',
  'youtu.be',
  'm.youtube.com',
]);

export function isContactEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

export function normalizeContactVideoUrl(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return '';
  return /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
}

export function isYouTubeUrl(value: string) {
  if (!value) return true;
  try {
    const host = new URL(value).hostname;
    return YOUTUBE_HOSTS.has(host);
  } catch {
    return false;
  }
}

export type ContactFormInput = {
  name: string;
  email: string;
  useCase: string;
  videoUrl: string;
  message: string;
};

type ContactFormFailure = { ok: false; error: string };
type ContactFormSuccess = {
  ok: true;
  mailto: { subject: string; body: string };
};

export function validateContactForm(input: ContactFormInput): ContactFormFailure | ContactFormSuccess {
  const name = input.name.trim();
  const email = input.email.trim();
  const useCase = input.useCase.trim();
  const videoUrl = normalizeContactVideoUrl(input.videoUrl);
  const message = input.message.trim();

  if (!name || !email || !useCase || !message) {
    return {
      ok: false,
      error: 'Please fill out name, email, use case, and the short note.',
    };
  }

  if (name.length > CONTACT_NAME_MAX || message.length > CONTACT_MESSAGE_MAX) {
    return {
      ok: false,
      error: `Keep the name under ${CONTACT_NAME_MAX} characters and the note under ${CONTACT_MESSAGE_MAX.toLocaleString()} characters.`,
    };
  }

  if (!isContactEmail(email)) {
    return { ok: false, error: 'Please enter a valid email address.' };
  }

  if (!isYouTubeUrl(videoUrl)) {
    return {
      ok: false,
      error: 'If you include a sample video, use a YouTube URL.',
    };
  }

  return {
    ok: true,
    mailto: {
      subject: `UVAI inbound: ${useCase}`,
      body: [
        `Name: ${name}`,
        `Email: ${email}`,
        `Use case: ${useCase}`,
        videoUrl ? `Sample video: ${videoUrl}` : 'Sample video: not provided',
        '',
        'Note:',
        message,
      ].join('\n'),
    },
  };
}