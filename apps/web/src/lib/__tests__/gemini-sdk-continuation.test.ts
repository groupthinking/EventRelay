import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GoogleGenAI, Type, type Fetch, type GenerateContentResponse } from '@google/genai';
import { geminiSampling } from '../gemini-parameters';

// Exercise the installed SDK's public API and HTTP serialization, not mocked
// models methods. All responses are synthetic transport fixtures; no provider
// credentials, billing, or claims about live model availability are involved.
type Payload = Record<string, unknown>;
const MODEL = 'gemini-3.8-flash';
const request = { model: MODEL, contents: 'Summarize the supplied evidence.' };

function response(text: string, finishReason = 'STOP', continuationToken?: string, groundingMetadata?: Payload): Payload {
  return {
    candidates: [{
      index: 0,
      content: { role: 'model', parts: [{ text }] },
      finishReason,
      ...(continuationToken ? { continuationToken } : {}),
      ...(groundingMetadata ? { groundingMetadata } : {}),
    }],
  };
}

function json(payload: Payload, status = 200): Response {
  return new Response(JSON.stringify(payload), { status, headers: { 'content-type': 'application/json' } });
}

function sse(...payloads: Payload[]): Response {
  return new Response(payloads.map((payload) => `data: ${JSON.stringify(payload)}\n\n`).join(''), {
    headers: { 'content-type': 'text/event-stream' },
  });
}

function harness(...hops: Array<Response | Error>) {
  const fetch = vi.fn<Fetch>(async () => {
    const hop = hops.shift();
    if (!hop) throw new Error('Unexpected SDK request: transport fixtures exhausted');
    if (hop instanceof Error) throw hop;
    return hop;
  });
  const client = new GoogleGenAI({
    apiKey: 'offline-test-key',
    vertexai: false,
    httpOptions: { fetch, retryOptions: { attempts: 1 } },
  });
  return { client, fetch };
}

async function collect(client: GoogleGenAI): Promise<GenerateContentResponse[]> {
  const chunks: GenerateContentResponse[] = [];
  for await (const chunk of await client.models.generateContentStream(request)) chunks.push(chunk);
  return chunks;
}

function grounding(label: string): Payload {
  return {
    groundingChunks: [{ web: { uri: `https://example.test/${label}`, title: label } }],
    groundingSupports: [{
      segment: { partIndex: 0, startIndex: 0, endIndex: label.length, text: label },
      groundingChunkIndices: [0],
    }],
    webSearchQueries: [label],
  };
}

beforeEach(() => {
  // Fail closed if a future SDK version bypasses the explicitly supplied fetch.
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Live network is forbidden in this test'); }));
});
afterEach(() => vi.unstubAllGlobals());

describe('installed Gemini SDK continuation contract', () => {
  it('joins unary hops and preserves grounding references to the correct parts and sources', async () => {
    const { client, fetch } = harness(
      json(response('first', 'CONTINUATION', 'checkpoint-1', grounding('first'))),
      json(response('second', 'STOP', undefined, grounding('second'))),
    );
    const result = await client.models.generateContent(request);
    expect(result.text).toBe('firstsecond');
    expect(fetch).toHaveBeenCalledTimes(2);
    const candidate = result.candidates?.[0];
    expect(candidate?.finishReason).toBe('STOP');
    expect(candidate?.continuationToken).toBeUndefined();
    expect(candidate?.groundingMetadata?.groundingChunks?.map((chunk) => chunk.web?.uri))
      .toEqual(['https://example.test/first', 'https://example.test/second']);
    expect(candidate?.groundingMetadata?.groundingSupports?.map((support) => ({
      part: support.segment?.partIndex, chunks: support.groundingChunkIndices,
    }))).toEqual([{ part: 0, chunks: [0] }, { part: 1, chunks: [1] }]);
    expect(candidate?.groundingMetadata?.webSearchQueries).toEqual(['first', 'second']);
  });

  it('recovers a dropped resumed request and an empty resumed stream without duplicating text', async () => {
    const { client, fetch } = harness(
      sse(response('first', 'CONTINUATION', 'checkpoint-1')),
      new TypeError('fetch failed'),
      sse(),
      sse(response('second')),
    );
    const chunks = await collect(client);
    expect(chunks.map((chunk) => chunk.text)).toEqual(['first', 'second']);
    expect(chunks[0].candidates?.[0]?.finishReason).toBeUndefined();
    expect(chunks[1].candidates?.[0]?.finishReason).toBe('STOP');
    expect(fetch).toHaveBeenCalledTimes(4);
    // Inspect actual serialized continuation requests below, without depending
    // on private SDK methods or state.
    for (const [, init] of fetch.mock.calls.slice(1)) {
      expect(JSON.parse(init?.body as string))
        .toHaveProperty('continuationToken', 'checkpoint-1');
    }
  });

  it.each(['unary', 'stream'] as const)('stops %s continuation on promptFeedback without candidates', async (mode) => {
    const blocked = { promptFeedback: { blockReason: 'SAFETY', blockReasonMessage: 'Blocked fixture' } };
    const { client, fetch } = harness(...(mode === 'unary'
      ? [json(response('partial', 'CONTINUATION', 'checkpoint-1')), json(blocked)]
      : [sse(response('partial', 'CONTINUATION', 'checkpoint-1')), sse(blocked)]));
    const result = mode === 'unary'
      ? await client.models.generateContent(request)
      : (await collect(client)).at(-1);
    expect(result?.promptFeedback?.blockReason).toBe('SAFETY');
    expect(result?.candidates?.[0]?.continuationToken).toBeUndefined();
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it('retains grounding metadata on streamed continuation chunks', async () => {
    const { client, fetch } = harness(
      sse(response('first', 'CONTINUATION', 'checkpoint-1', grounding('first'))),
      sse(response('second', 'STOP', undefined, grounding('second'))),
    );
    const chunks = await collect(client);
    expect(chunks.map((chunk) => chunk.candidates?.[0]?.groundingMetadata))
      .toEqual([grounding('first'), grounding('second')]);
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it('does not resume an earlier checkpoint after a safety-blocked streaming chunk', async () => {
    const { client, fetch } = harness(sse(
      { candidates: [{ content: { role: 'model', parts: [{ text: 'partial' }] }, continuationToken: 'checkpoint-1' }] },
      { promptFeedback: { blockReason: 'SAFETY' } },
    ));
    const chunks = await collect(client);
    expect(chunks.at(-1)?.promptFeedback?.blockReason).toBe('SAFETY');
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it.each(['unary', 'stream'] as const)('surfaces a rejected %s continuation request without retrying it', async (mode) => {
    const { client, fetch } = harness(
      mode === 'unary' ? json(response('partial', 'CONTINUATION', 'checkpoint-1'))
        : sse(response('partial', 'CONTINUATION', 'checkpoint-1')),
      json({ error: { code: 403, message: 'PERMISSION_DENIED', status: 'PERMISSION_DENIED' } }, 403),
    );
    const result = mode === 'unary' ? client.models.generateContent(request) : collect(client);
    await expect(result).rejects.toMatchObject({ name: 'ApiError', status: 403 });
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it('preserves the transport error after bounded empty-hop retries', async () => {
    const { client, fetch } = harness(
      sse(response('partial', 'CONTINUATION', 'checkpoint-1')),
      new TypeError('connection reset'), sse(), sse(), sse(),
    );
    await expect(collect(client)).rejects.toThrow('connection reset');
    expect(fetch).toHaveBeenCalledTimes(5);
  });

  it('does not retry a caller abort', async () => {
    const abort = new Error('caller canceled');
    abort.name = 'AbortError';
    const { client, fetch } = harness(sse(response('partial', 'CONTINUATION', 'checkpoint-1')), abort);
    await expect(collect(client)).rejects.toThrow('caller canceled');
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it.each(['gemini-3.8-flash', 'gemini-2.5-flash'])('serializes structured extraction parameters for %s', async (model) => {
    const { client, fetch } = harness(json(response('{"summary":"evidence"}')));
    await client.models.generateContent({
      ...request, model,
      config: {
        ...geminiSampling(model, 0.3),
        responseMimeType: 'application/json',
        responseSchema: { type: Type.OBJECT, properties: { summary: { type: Type.STRING } }, required: ['summary'] },
      },
    });
    const [url, init] = fetch.mock.calls[0];
    const body = JSON.parse(init?.body as string);
    expect(String(url)).toContain(`${model}:generateContent`);
    expect(body.generationConfig.responseMimeType).toBe('application/json');
    expect(body.generationConfig.responseSchema.required).toEqual(['summary']);
    expect(body.generationConfig.temperature).toBe(model === 'gemini-2.5-flash' ? 0.3 : undefined);
  });
});
