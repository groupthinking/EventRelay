'use client';

import { useCallback, useState } from 'react';

const TEAL = '#6af2de';
const TEAL_DEEP = '#10b7a5';
const INK = '#f8f5fd';
const BORDER = 'rgba(72, 71, 77, 0.18)';
const MUTED = 'rgba(248,245,253,0.55)';
const FAINT = 'rgba(248,245,253,0.35)';

const USE_CASES = [
  'Engineering workflow',
  'Content workflow',
  'Research workflow',
  'Business operations workflow',
  'Other video-to-action workflow',
];

const DEFAULT_CONTACT_EMAIL = 'viralnowsales@gmail.com';
const CONTACT_EMAIL =
  process.env.NEXT_PUBLIC_CONTACT_EMAIL && process.env.NEXT_PUBLIC_CONTACT_EMAIL.trim().length > 0
    ? process.env.NEXT_PUBLIC_CONTACT_EMAIL
    : DEFAULT_CONTACT_EMAIL;

const MESSAGE_MAX = 1000;
const NAME_MAX = 100;

function isEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function isYouTube(value: string) {
  if (!value) return true;
  const candidate = /^https?:\/\//i.test(value) ? value : `https://${value}`;
  try {
    const u = new URL(candidate);
    return ['youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com'].includes(u.hostname);
  } catch {
    return false;
  }
}

type FormStatus = { kind: 'idle' | 'pending' | 'error'; text: string };

export default function ContactForm() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [useCase, setUseCase] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState<FormStatus>({ kind: 'idle', text: '' });

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const n = name.trim();
      const em = email.trim();
      const uc = useCase.trim();
      const v = videoUrl.trim();
      const msg = message.trim();

      if (!n || !em || !uc || !msg) {
        setStatus({ kind: 'error', text: 'Please fill out name, email, use case, and the short note.' });
        return;
      }
      if (n.length > NAME_MAX || msg.length > MESSAGE_MAX) {
        setStatus({
          kind: 'error',
          text: `Keep the name under ${NAME_MAX} characters and the note under ${MESSAGE_MAX.toLocaleString()} characters.`,
        });
        return;
      }
      if (!isEmail(em)) {
        setStatus({ kind: 'error', text: 'Please enter a valid email address.' });
        return;
      }
      if (!isYouTube(v)) {
        setStatus({ kind: 'error', text: 'If you include a sample video, use a YouTube URL.' });
        return;
      }

      const subject = encodeURIComponent('UVAI inbound: ' + uc);
      const body = encodeURIComponent(
        [
          'Name: ' + n,
          'Email: ' + em,
          'Use case: ' + uc,
          v ? 'Sample video: ' + v : 'Sample video: not provided',
          '',
          'Note:',
          msg,
        ].join('\n'),
      );

      setStatus({ kind: 'pending', text: 'Trying to open your email app...' });
      window.location.href = `mailto:${CONTACT_EMAIL}?subject=${subject}&body=${body}`;
    },
    [name, email, useCase, videoUrl, message],
  );

  return (
    <article
      className="rounded-2xl p-7"
      style={{ background: 'rgba(19,19,24,0.65)', border: `1px solid ${BORDER}` }}
    >
      <h3 className="font-heading text-xl font-bold mb-2" style={{ color: INK }}>
        Workflow request
      </h3>
      <p className="text-sm mb-5" style={{ color: MUTED }}>
        Four fields. Enough to start a useful conversation.
      </p>
      <form onSubmit={handleSubmit} className="grid gap-4" noValidate>
        <Field label="Name" htmlFor="name">
          <input
            id="name"
            name="name"
            autoComplete="name"
            placeholder="Your name"
            maxLength={NAME_MAX}
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="form-input"
          />
        </Field>
        <Field label="Email" htmlFor="email">
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            placeholder="you@company.com"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="form-input"
          />
        </Field>
        <Field label="Use case" htmlFor="use_case">
          <select
            id="use_case"
            name="use_case"
            required
            value={useCase}
            onChange={(e) => setUseCase(e.target.value)}
            className="form-input"
          >
            <option value="">Choose one</option>
            {USE_CASES.map((opt) => (
              <option key={opt}>{opt}</option>
            ))}
          </select>
        </Field>
        <Field label="Sample YouTube URL" htmlFor="video_url">
          <input
            id="video_url"
            name="video_url"
            type="text"
            inputMode="url"
            autoComplete="url"
            spellCheck={false}
            placeholder="youtube.com/watch?v=..."
            aria-describedby="video_url_hint"
            value={videoUrl}
            onChange={(e) => setVideoUrl(e.target.value)}
            className="form-input"
          />
          <span id="video_url_hint" className="text-xs" style={{ color: FAINT }}>
            Optional. YouTube link, with or without https://.
          </span>
        </Field>
        <Field label="What should the output be?" htmlFor="message">
          <textarea
            id="message"
            name="message"
            placeholder="Example: turn product demo videos into API docs and tickets."
            maxLength={MESSAGE_MAX}
            required
            rows={4}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            className="form-input"
          />
        </Field>
        <p
          role="status"
          aria-live="polite"
          className="text-sm min-h-[1.25rem]"
          style={{
            color:
              status.kind === 'pending'
                ? TEAL
                : status.kind === 'error'
                  ? '#ff8a8a'
                  : FAINT,
          }}
        >
          {status.text}
        </p>
        <button
          type="submit"
          className="px-6 py-3 rounded-lg font-bold text-sm transition-all duration-300 active:scale-95"
          style={{ background: `linear-gradient(135deg, ${TEAL}, ${TEAL_DEEP})`, color: '#002b26' }}
        >
          Send request
        </button>
      </form>

      <style jsx>{`
        .form-input {
          width: 100%;
          padding: 0.7rem 0.9rem;
          border-radius: 0.55rem;
          background: rgba(14, 14, 19, 0.7);
          border: 1px solid ${BORDER};
          color: ${INK};
          font-size: 0.9rem;
          transition: border-color 0.2s, box-shadow 0.2s;
        }
        .form-input::placeholder {
          color: rgba(248, 245, 253, 0.3);
        }
        .form-input:focus {
          outline: none;
          border-color: ${TEAL};
          box-shadow: 0 0 0 3px rgba(106, 242, 222, 0.15);
        }
        select.form-input {
          appearance: none;
          background-image: linear-gradient(45deg, transparent 50%, ${TEAL} 50%),
            linear-gradient(135deg, ${TEAL} 50%, transparent 50%);
          background-position: calc(100% - 18px) 50%, calc(100% - 13px) 50%;
          background-size: 5px 5px, 5px 5px;
          background-repeat: no-repeat;
          padding-right: 2.2rem;
        }
        textarea.form-input {
          resize: vertical;
          min-height: 100px;
        }
      `}</style>
    </article>
  );
}

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <label htmlFor={htmlFor} className="grid gap-1.5">
      <span
        className="text-[11px] font-bold uppercase tracking-widest"
        style={{ color: 'rgba(248,245,253,0.65)' }}
      >
        {label}
      </span>
      {children}
    </label>
  );
}
