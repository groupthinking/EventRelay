export const runtime = 'nodejs';

const OPENAI_REALTIME_CALLS_URL = 'https://api.openai.com/v1/realtime/calls';
const OPENAI_REALTIME_CLIENT_SECRETS_URL = 'https://api.openai.com/v1/realtime/client_secrets';

const realtimeSession = {
  type: 'realtime',
  model: 'gpt-realtime-2',
  instructions:
    'Help users turn video content into safe, useful workflows. Keep responses concise, practical, and focused on the requested outcome.',
  audio: {
    input: {
      turn_detection: {
        type: 'server_vad',
      },
    },
    output: {
      voice: 'marin',
    },
  },
  reasoning: {
    effort: 'low',
  },
  tools: [
    {
      type: 'function',
      name: 'check_calendar',
      description: 'Check whether a requested review or workflow handoff time is available.',
      parameters: {
        type: 'object',
        properties: {
          date: {
            type: 'string',
            description: 'Requested calendar date.',
          },
          time: {
            type: 'string',
            description: 'Requested time in 24-hour local time, such as 14:30.',
          },
        },
        required: ['date', 'time'],
        additionalProperties: false,
      },
    },
  ],
  tool_choice: 'auto',
};

/**
 * OpenAI error bodies routinely echo org/project identifiers, quota state and,
 * on a 401, a partial API key (`Incorrect API key provided: sk-proj-****ABCD`).
 * None of that may reach the browser, so the upstream body is logged
 * server-side only and the caller gets a fixed 502 with a static message.
 * The upstream status is deliberately NOT mirrored — it is itself a signal
 * about the server's OpenAI account state.
 */
function upstreamFailure(
  stage: string,
  status: number,
  body: string,
  error: string,
  code: string,
): Response {
  console.error(`[realtime] ${stage} failed`, JSON.stringify({ status, body }));

  return Response.json({ error, code }, { status: 502 });
}

/**
 * A transport-level failure — DNS, TLS, connection reset, timeout — rejects the
 * fetch before any upstream status exists, so `upstreamFailure` never runs.
 * Left unhandled it escapes to Next.js's own 500, which is not the JSON shape
 * the client parses and which produces no `[realtime]` log line. The cause is
 * an Error from our own transport, not upstream text, so it is safe to log —
 * and the caller gets the same fixed 502 as a non-OK upstream response.
 */
function upstreamUnreachable(
  stage: string,
  cause: unknown,
  error: string,
  code: string,
): Response {
  console.error(`[realtime] ${stage} request failed`, cause);

  return Response.json({ error, code }, { status: 502 });
}

function getOpenAiHeaders(contentType?: string): Record<string, string> | null {
  const apiKey = process.env.OPENAI_API_KEY;

  if (!apiKey) {
    return null;
  }

  const headers: Record<string, string> = {
    Authorization: `Bearer ${apiKey}`,
  };

  if (contentType) {
    headers['Content-Type'] = contentType;
  }

  const safetyIdentifier = process.env.OPENAI_SAFETY_IDENTIFIER;
  if (safetyIdentifier) {
    headers['OpenAI-Safety-Identifier'] = safetyIdentifier;
  }

  return headers;
}

export async function GET() {
  const headers = getOpenAiHeaders('application/json');

  if (!headers) {
    return Response.json(
      {
        error: 'OPENAI_API_KEY is not configured on the server.',
        code: 'realtime_not_configured',
      },
      { status: 500 },
    );
  }

  let upstream: Response;
  let body: string;

  try {
    upstream = await fetch(OPENAI_REALTIME_CLIENT_SECRETS_URL, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        expires_after: {
          anchor: 'created_at',
          seconds: 600,
        },
        session: realtimeSession,
      }),
    });

    body = await upstream.text();
  } catch (err) {
    return upstreamUnreachable(
      'client_secret',
      err,
      'OpenAI Realtime client secret creation failed.',
      'realtime_client_secret_failed',
    );
  }

  const contentType = upstream.headers.get('content-type') || 'application/json';

  if (!upstream.ok) {
    return upstreamFailure(
      'client_secret',
      upstream.status,
      body,
      'OpenAI Realtime client secret creation failed.',
      'realtime_client_secret_failed',
    );
  }

  return new Response(body, {
    status: upstream.status,
    headers: {
      'Content-Type': contentType,
      'Cache-Control': 'no-store',
    },
  });
}

export async function POST(request: Request) {
  const offerSdp = await request.text();
  if (!offerSdp.trim() || !offerSdp.includes('v=0')) {
    return Response.json(
      { error: 'A valid WebRTC SDP offer is required.', code: 'invalid_sdp_offer' },
      { status: 400 },
    );
  }

  const headers = getOpenAiHeaders();

  if (!headers) {
    return Response.json(
      {
        error: 'OPENAI_API_KEY is not configured on the server.',
        code: 'realtime_not_configured',
      },
      { status: 500 },
    );
  }

  const formData = new FormData();
  formData.set('sdp', new Blob([offerSdp], { type: 'application/sdp' }), 'offer.sdp');
  formData.set('session', new Blob([JSON.stringify(realtimeSession)], { type: 'application/json' }), 'session.json');

  let upstream: Response;
  let body: string;

  try {
    upstream = await fetch(OPENAI_REALTIME_CALLS_URL, {
      method: 'POST',
      headers,
      body: formData,
    });

    body = await upstream.text();
  } catch (err) {
    return upstreamUnreachable(
      'sdp_exchange',
      err,
      'OpenAI Realtime session creation failed.',
      'realtime_session_failed',
    );
  }

  if (!upstream.ok) {
    return upstreamFailure(
      'sdp_exchange',
      upstream.status,
      body,
      'OpenAI Realtime session creation failed.',
      'realtime_session_failed',
    );
  }

  return new Response(body, {
    status: upstream.status,
    headers: {
      'Content-Type': 'application/sdp',
    },
  });
}
