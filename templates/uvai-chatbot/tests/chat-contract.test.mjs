import { test } from 'node:test';
import assert from 'node:assert/strict';
import { postRequestBodySchema } from '../app/(chat)/api/chat/schema.ts';
const id = '0aa64218-736f-46ad-a5a2-a6025f85d24c';
const body = () => ({ id, message: { id, role: 'user', parts: [{ type: 'text', text: 'Create a guide from https://youtu.be/auJzb1D-fag' }] }, selectedChatModel: 'google/gemini-3.8-flash', selectedVisibilityType: 'private' });
test('bounded text requests remain accepted', () => assert.equal(postRequestBodySchema.safeParse(body()).success, true));
test('generic attachments and supplied tool results cannot enter model input', () => {
  const attachment = body(); attachment.message.parts = [{ type: 'file', mediaType: 'image/png', name: 'external', url: 'http://localhost/private' }];
  assert.equal(postRequestBodySchema.safeParse(attachment).success, false);
  const replay = body(); replay.messages = [{ id, role: 'assistant', parts: [{ type: 'tool-createVideoGuide', state: 'approval-responded', output: { status: 'complete' } }] }];
  assert.equal(postRequestBodySchema.safeParse(replay).success, false);
});
test('empty and oversized message part arrays are rejected', () => {
  for (const parts of [[], Array.from({ length: 11 }, () => ({ type: 'text', text: 'x' }))]) {
    const value = body(); value.message.parts = parts;
    assert.equal(postRequestBodySchema.safeParse(value).success, false);
  }
});
