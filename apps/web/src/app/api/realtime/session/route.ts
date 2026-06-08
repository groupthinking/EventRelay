export const runtime = 'nodejs';

const OPENAI_REALTIME_CALLS_URL = 'https://api.openai.com/v1/realtime/calls';

const sessionConfig = {
  type: 'realtime',
  model: 'gpt-realtime-2',
  instructions:
    'Help users turn video content into safe, useful workflows. Keep responses concise, practical, and focused on the requested outcome.',
  audio: {
    output: {
      voice: 'marin',
    },
  },
  reasoning: {
    effort: 'low',
  },
};

export async function POST(request: Request) {
  const offerSdp = await request.text();
  if (!offerSdp.trim() || !offerSdp.includes('v=0')) {
    return Response.json(
      { error: 'A valid WebRTC SDP offer is required.' },
      { status: 400 },
    );
  }

  const apiKey = process.env.OPENAI_API_KEY;

  if (!apiKey) {
    return Response.json(
      { error: 'OPENAI_API_KEY is not configured on the server.' },
      { status: 500 },
    );
  }

  const formData = new FormData();
  formData.set('sdp', offerSdp);
  formData.set('session', JSON.stringify(sessionConfig));

  const headers: Record<string, string> = {
    Authorization: `Bearer ${apiKey}`,
  };

  const safetyIdentifier = process.env.OPENAI_SAFETY_IDENTIFIER;
  if (safetyIdentifier) {
    headers['OpenAI-Safety-Identifier'] = safetyIdentifier;
  }

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
