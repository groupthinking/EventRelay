import { describe, it, expect, afterEach, vi } from 'vitest';
import { POST } from '@/app/api/transcribe/route';

vi.mock('@/lib/transcription-service', () => ({
  fetchTranscript: vi.fn(),
}));

import { fetchTranscript } from '@/lib/transcription-service';

afterEach(() => {
  vi.restoreAllMocks();
  // restoreAllMocks only restores spies; the module-factory vi.fn() keeps its
  // call history, which would leak across tests in this file.
  vi.clearAllMocks();
});

function transcribeRequest(body: string): Request {
  return new Request('http://localhost/api/transcribe', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body,
  });
}

describe('POST /api/transcribe error leakage', () => {
  it('does not echo raw upstream provider text when the pipeline throws', async () => {
    const upstreamMessage =
      'OpenAI 401: Incorrect API key provided: sk-proj-****ABCD (org org-eventrelay-prod)';
    vi.mocked(fetchTranscript).mockRejectedValue(new Error(upstreamMessage));
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    const res = await POST(
      transcribeRequest(JSON.stringify({ url: 'https://www.youtube.com/watch?v=auJzb1D-fag' })),
    );
    const raw = await res.text();

    expect(res.status).toBe(500);
    expect(JSON.parse(raw)).toEqual({
      success: false,
      error: 'Transcription failed',
      code: 'transcription_failed',
      transcript: '',
    });
    for (const token of ['sk-proj', 'org-eventrelay-prod', 'Incorrect API key']) {
      expect(raw).not.toContain(token);
    }

    // Raw detail is retained for operators only.
    expect(consoleError).toHaveBeenCalledWith(
      'Transcription route error:',
      expect.objectContaining({ message: upstreamMessage }),
    );
  });

  it('does not echo parser internals for a malformed body', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    const res = await POST(transcribeRequest('{not json'));
    const raw = await res.text();

    expect(res.status).toBe(400);
    expect(JSON.parse(raw)).toEqual({
      success: false,
      error: 'Invalid JSON in request body',
      code: 'invalid_json',
      transcript: '',
    });
    expect(raw).not.toContain('Unexpected token');
    expect(raw).not.toContain('position');
    expect(raw).not.toContain('details');
    expect(consoleError).toHaveBeenCalled();
  });
});

describe('POST /api/transcribe error-code contract', () => {
  it('returns input_required when neither url nor audioUrl is supplied', async () => {
    const res = await POST(transcribeRequest(JSON.stringify({ language: 'en' })));
    const body = await res.json();

    expect(res.status).toBe(400);
    expect(body).toMatchObject({
      success: false,
      error: 'Either url or audioUrl is required',
      code: 'input_required',
    });
    // fetchTranscript must not be reached on a missing-input request.
    expect(vi.mocked(fetchTranscript)).not.toHaveBeenCalled();
  });

  // Every resolved-failure branch keeps fetchTranscript's app-authored message in
  // `error` and gains a stable `code`. The mocked messages below carry provider-
  // shaped tokens purely to prove none of them can reach the client via `code`,
  // `details` or any other added field.
  const resolvedFailures = [
    {
      name: 'input_required',
      serviceError: 'url or audioUrl is required',
      status: 400,
      code: 'input_required',
    },
    {
      name: 'rate_limited',
      serviceError: 'OpenAI rate limit reached',
      status: 429,
      code: 'rate_limited',
    },
    {
      name: 'billing_not_configured',
      serviceError: 'Gemini billing is not enabled',
      status: 500,
      code: 'billing_not_configured',
    },
    {
      name: 'transcription_unavailable',
      serviceError: 'Could not transcribe video — all strategies failed',
      status: 503,
      code: 'transcription_unavailable',
    },
  ] as const;

  for (const branch of resolvedFailures) {
    it(`returns ${branch.name} with the service message preserved`, async () => {
      vi.mocked(fetchTranscript).mockResolvedValue({
        success: false,
        error: branch.serviceError,
        transcript: '',
      });

      const res = await POST(
        transcribeRequest(JSON.stringify({ url: 'https://www.youtube.com/watch?v=auJzb1D-fag' })),
      );
      const raw = await res.text();
      const body = JSON.parse(raw);

      expect(res.status).toBe(branch.status);
      expect(body.code).toBe(branch.code);
      expect(body.success).toBe(false);
      expect(body.transcript).toBe('');
      // The human-facing string contract is unchanged.
      expect(body.error).toBe(branch.serviceError);
      // No provider credential material is introduced by the added fields.
      for (const token of ['sk-proj', 'sk_live', 'org-eventrelay-prod', 'Bearer ']) {
        expect(raw).not.toContain(token);
      }
    });
  }
});
