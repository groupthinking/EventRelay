export type HostedSpecHealthReasonCode =
  | 'HOSTED_SPEC_READY'
  | 'HOSTED_SPEC_INCOMPLETE'
  | 'HOSTED_PACK_NOT_FOUND'
  | 'HOSTED_PACK_PROCESSING'
  | 'HOSTED_PACK_EXTRACT_FAILED'
  | 'HOSTED_PACK_IDENTITY_ONLY';

export type HostedSpecUnavailableHealth = {
  ok: boolean;
  status: number;
  checked_at: string;
  detail?: string;
  reason_code?: HostedSpecHealthReasonCode;
};

export type HostedSpecUnavailablePageProps = {
  videoId: string;
  health: HostedSpecUnavailableHealth;
};

function hostedSpecLivePath(videoId: string): string {
  return `/d/${encodeURIComponent(videoId.trim())}`;
}

function titleForReason(reason: HostedSpecHealthReasonCode | undefined): string {
  switch (reason) {
    case 'HOSTED_PACK_NOT_FOUND':
      return 'Video pack not found';
    case 'HOSTED_PACK_PROCESSING':
      return 'Video pack is still processing';
    case 'HOSTED_PACK_EXTRACT_FAILED':
      return 'Pack extraction did not complete';
    case 'HOSTED_PACK_IDENTITY_ONLY':
      return 'Compiled spec is not available for this pack';
    case 'HOSTED_SPEC_INCOMPLETE':
      return 'Hosted spec is incomplete';
    case 'HOSTED_SPEC_READY':
      return 'Hosted app not ready';
    default:
      return 'Hosted app not available';
  }
}

function summaryForReason(reason: HostedSpecHealthReasonCode | undefined): string {
  switch (reason) {
    case 'HOSTED_PACK_NOT_FOUND':
      return 'There is no stored Video Pack for this ID yet. Generate a pack in Studio before this URL can serve a compiled app.';
    case 'HOSTED_PACK_PROCESSING':
      return 'A pack job may still be running. This page will not fabricate a compiled spec while processing is in flight.';
    case 'HOSTED_PACK_EXTRACT_FAILED':
      return 'Extraction failed with a recorded error. Retrying from here does not invent a new pack; use Studio only if you intend to run extraction again.';
    case 'HOSTED_PACK_IDENTITY_ONLY':
      return 'This pack is identity-only and has no compiled hosted spec to run at /d.';
    case 'HOSTED_SPEC_INCOMPLETE':
      return 'The compiled spec is missing required files and cannot be served.';
    default:
      return 'This hosted app cannot be served at this URL until pack health reports ready.';
  }
}

export function HostedSpecUnavailablePage({ videoId, health }: HostedSpecUnavailablePageProps) {
  const id = videoId.trim();
  const reason = health.reason_code ?? 'HOSTED_PACK_EXTRACT_FAILED';
  const detail = health.detail?.trim() || 'No additional detail was recorded.';
  const title = titleForReason(reason);
  const summary = summaryForReason(reason);
  const healthPath = `${hostedSpecLivePath(id)}/health`;
  const studioHref = `/studio?video=${encodeURIComponent(`https://www.youtube.com/watch?v=${id}`)}`;

  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>{title} — {id}</title>
        <style>{`
          :root {
            color-scheme: light dark;
            --bg: #fafafa;
            --surface: #ffffff;
            --border: #e4e4e7;
            --muted: #71717a;
            --text: #18181b;
            --accent: #0d9488;
            --accent-hover: #0f766e;
            --code-bg: #f4f4f5;
            --field-bg: #fafafa;
          }
          @media (prefers-color-scheme: dark) {
            :root {
              --bg: #09090b;
              --surface: #18181b;
              --border: #3f3f46;
              --muted: #a1a1aa;
              --text: #fafafa;
              --accent: #2dd4bf;
              --accent-hover: #5eead4;
              --code-bg: #27272a;
              --field-bg: #09090b;
            }
          }
          * { box-sizing: border-box; }
          body {
            margin: 0;
            min-height: 100dvh;
            font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
            font-size: 14px;
            line-height: 1.5;
            color: var(--text);
            background: var(--bg);
            -webkit-font-smoothing: antialiased;
          }
          .page {
            display: flex;
            min-height: 100dvh;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
          }
          [data-slot="empty"] {
            width: 100%;
            max-width: 28rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1.25rem;
            text-align: center;
            padding: 2rem 1.5rem;
            border: 1px dashed var(--border);
            border-radius: 0.75rem;
            background: var(--surface);
          }
          [data-slot="empty-header"] {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
            max-width: 24rem;
          }
          [data-slot="empty-icon"] {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 0.5rem;
            background: var(--code-bg);
            color: var(--muted);
            font-size: 1.125rem;
            margin-bottom: 0.25rem;
          }
          [data-slot="empty-title"] {
            font-size: 1.125rem;
            font-weight: 600;
            letter-spacing: -0.02em;
          }
          [data-slot="empty-description"] {
            color: var(--muted);
            font-size: 0.875rem;
            line-height: 1.6;
          }
          [data-slot="empty-content"] {
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            text-align: left;
          }
          .field {
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
            padding: 0.75rem 0.875rem;
            border-radius: 0.5rem;
            border: 1px solid var(--border);
            background: var(--field-bg);
          }
          .field-label {
            font-size: 0.6875rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--muted);
          }
          .field-value {
            font-size: 0.8125rem;
            word-break: break-word;
          }
          code, .reason-code {
            font-family: ui-monospace, "JetBrains Mono", "SF Mono", Menlo, monospace;
            font-size: 0.8125rem;
          }
          .reason-code {
            display: inline-block;
            padding: 0.15rem 0.4rem;
            border-radius: 0.25rem;
            background: var(--code-bg);
            color: var(--text);
          }
          .actions {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            justify-content: center;
            width: 100%;
            margin-top: 0.25rem;
          }
          .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0.5rem 0.875rem;
            border-radius: 0.375rem;
            font-size: 0.8125rem;
            font-weight: 500;
            text-decoration: none;
            border: 1px solid var(--border);
            color: var(--text);
            background: transparent;
          }
          .btn-primary {
            border-color: transparent;
            background: var(--accent);
            color: #042f2e;
          }
          @media (prefers-color-scheme: dark) {
            .btn-primary { color: #042f2e; }
          }
          .btn:hover { opacity: 0.92; }
          .meta {
            font-size: 0.75rem;
            color: var(--muted);
            text-align: center;
            line-height: 1.5;
          }
        `}</style>
      </head>
      <body>
        <div className="page">
          <main data-slot="empty" data-hosted-unavailable="true">
            <div data-slot="empty-header">
              <div data-slot="empty-icon" aria-hidden="true">◇</div>
              <h1 data-slot="empty-title">{title}</h1>
              <p data-slot="empty-description">{summary}</p>
            </div>
            <div data-slot="empty-content">
              <div className="field">
                <span className="field-label">Video ID</span>
                <span className="field-value">
                  <code>{id}</code>
                </span>
              </div>
              <div className="field">
                <span className="field-label">Reason code</span>
                <span className="field-value">
                  <span className="reason-code" data-reason-code={reason}>{reason}</span>
                </span>
              </div>
              <div className="field">
                <span className="field-label">Detail</span>
                <span className="field-value">{detail}</span>
              </div>
            </div>
            <div className="actions">
              <a className="btn btn-primary" href={studioHref}>Open in Studio</a>
              <a className="btn" href={healthPath}>Health probe</a>
            </div>
            <p className="meta">
              GET <code>{healthPath}</code> returns HTTP 200 with <code>health.reason_code</code> (unchanged contract).
            </p>
          </main>
        </div>
      </body>
    </html>
  );
}
