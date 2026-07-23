import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { describe, expect, it } from 'vitest';

const webSrc = join(dirname(fileURLToPath(import.meta.url)), '../..');

function readSource(relativePath: string) {
  return readFileSync(join(webSrc, relativePath), 'utf8');
}

describe('video-generator accessibility', () => {
  const source = readSource('components/video-generator.tsx');

  it('disables the generate button when the prompt is empty', () => {
    // The disabled attribute must include the empty-prompt guard.
    expect(source).toContain('!prompt.trim()');
    expect(source).toMatch(/disabled=\{[^}]*!prompt\.trim\(\)[^}]*\}/);
  });

  it('associates aria-describedby with the visible explanation when the prompt is empty', () => {
    // When the prompt is empty the button must reference the explanation element.
    expect(source).toContain("aria-describedby={!prompt.trim() ? 'video-generate-requirement' : undefined}");
    // The explanation element must carry the matching id.
    expect(source).toContain('id="video-generate-requirement"');
  });

  it('renders the visible explanation only when the prompt is empty', () => {
    // The explanation paragraph must be conditionally rendered on !prompt.trim().
    expect(source).toMatch(/\{!prompt\.trim\(\)\s*&&[\s\S]*?id="video-generate-requirement"/);
  });

  it('removes aria-describedby when the prompt has non-whitespace content', () => {
    // The ternary must resolve to undefined when a prompt is present, so the
    // description is absent for sighted and AT users alike.
    expect(source).toContain("? 'video-generate-requirement' : undefined");
  });
});
