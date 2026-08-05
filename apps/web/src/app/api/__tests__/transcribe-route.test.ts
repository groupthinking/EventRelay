import { describe, it, expect, afterEach, vi } from 'vitest';
import { POST } from '@/app/api/transcribe/route';

vi.mock('@/lib/transcription-service', () => ({
  fetchTranscript: vi.fn(),
}));

import { fetchTranscript } from '@/lib/transcription-service';

afterEach(() => {
  vi.restoreAllMocks();
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
