import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { describe, expect, it } from 'vitest';

const webSrc = join(dirname(fileURLToPath(import.meta.url)), '../..');

function readSource(relativePath: string) {
  return readFileSync(join(webSrc, relativePath), 'utf8');
}

describe('landing style safety', () => {
  it('keeps one clear heading for the YouTube URL to Studio workflow', () => {
    const source = readSource('app/page.tsx');
    expect(source.match(/<h1\b/g)).toHaveLength(1);
    expect(source).toContain('Turn YouTube into bound tasks.');
  });

  it('promises review of proposed work instead of approval', () => {
    const source = readSource('app/page.tsx');
    expect(source).toContain(
      'Studio prepares proposed work and build rails for you to review.',
    );
    expect(source).not.toMatch(/\bapprov(?:e|al|ed|ing)\b/i);
  });
});
