import { beforeEach, describe, expect, it, vi } from 'vitest';

const { acquireLoomAudio, transcribeWithXai, grokChatCompletion } = vi.hoisted(() => ({
  acquireLoomAudio: vi.fn(),
  transcribeWithXai: vi.fn(),
  grokChatCompletion: vi.fn(),
}));

vi.mock('@/lib/loom-audio', () => ({
  acquireLoomAudio,
}));

vi.mock('@/lib/xai-stt', () => ({
  transcribeWithXai,
}));

vi.mock('@/lib/billing/grok-client', () => ({
  grokChatCompletion,
}));

import { buildFromLoomShare } from '@/lib/loom-pro-build';

const SHARE = 'https://www.loom.com/share/c43a642f815f4378b6f80a889bb73d8d';
const MP4 = 'https://cdn.loom.com/sessions/transcoded/c43a642f815f4378b6f80a889bb73d8d.mp4?Policy=test';

beforeEach(() => {
  acquireLoomAudio.mockReset();
  transcribeWithXai.mockReset();
  grokChatCompletion.mockReset();
});

describe('buildFromLoomShare', () => {
  it('feeds the xAI transcript into grokChatCompletion and returns provider xai', async () => {
    acquireLoomAudio.mockResolvedValue({
      mode: 'url',
      mediaUrl: MP4,
      contentType: 'video/mp4',
      source: 'transcoded-url',
      share: { videoId: 'c43a642f815f4378b6f80a889bb73d8d', shareUrl: SHARE },
    });
    transcribeWithXai.mockResolvedValue({
      text: 'Ship the queue worker next.',
      duration: 18.2,
      model: 'grok-voice-transcribe-2.0',
    });
    grokChatCompletion.mockResolvedValue({
      answer: 'Build a queue worker with a single retry rail.',
      model: 'grok-4-1-fast',
      provider: 'xai',
    });

    const built = await buildFromLoomShare(SHARE, 'grok-4-1-fast');
    expect(transcribeWithXai).toHaveBeenCalledWith({ url: MP4 });
    const prompt = grokChatCompletion.mock.calls[0]?.[0] as string;
    expect(prompt).toContain('Ship the queue worker next.');
    expect(prompt).not.toContain(MP4);
    expect(grokChatCompletion.mock.calls[0]?.[1]).toBe('grok-4-1-fast');
    expect(built.provider).toBe('xai');
    expect(built.answer).toContain('queue worker');
    expect(built.duration).toBe(18.2);
    expect(built.transcript).toBe('Ship the queue worker next.');
  });
});
