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

function getOpenAiHeaders(contentType?: string) {
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
      { error: 'OPENAI_API_KEY is not configured on the server.' },
      { status: 500 },
    );
  }

  const upstream = await fetch(OPENAI_REALTIME_CLIENT_SECRETS_URL, {
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

  const body = await upstream.text();
  const contentType = upstream.headers.get('content-type') || 'application/json';

  if (!upstream.ok) {
    return Response.json(
      {
        error: 'OpenAI Realtime client secret creation failed.',
        details: body,
      },
      { status: upstream.status },
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
      { error: 'A valid WebRTC SDP offer is required.' },
      { status: 400 },
    );
  }

  const headers = getOpenAiHeaders();

  if (!headers) {
    return Response.json(
      { error: 'OPENAI_API_KEY is not configured on the server.' },
      { status: 500 },
    );
  }

  const formData = new FormData();
  formData.set('sdp', new Blob([offerSdp], { type: 'application/sdp' }), 'offer.sdp');
  formData.set('session', new Blob([JSON.stringify(realtimeSession)], { type: 'application/json' }), 'session.json');

  const upstream = await fetch(OPENAI_REALTIME_CALLS_URL, {
    method: 'POST',
    headers,
    body: formData,
  });

  const body = await upstream.text();

  if (!upstream.ok) {
    return Response.json(
      {
        error: 'OpenAI Realtime session creation failed.',
        details: body,
      },
      { status: upstream.status },
    );
  }

  return new Response(body, {
    status: upstream.status,
    headers: {
      'Content-Type': 'application/sdp',
    },
  });
}
