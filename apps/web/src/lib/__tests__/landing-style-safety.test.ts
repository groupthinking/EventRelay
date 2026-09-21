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
    expect(source).toContain('Turn a YouTube URL into a hashed Video Pack, then open it in Studio.');
  });

  it('ContactForm does not use styled-jsx (breaks strict TS builds)', () => {
    const source = readSource('app/ContactForm.tsx');
    expect(source).not.toContain('<style jsx>');
  });

  it('HeroSection does not use styled-jsx (breaks strict TS builds)', () => {
    const source = readSource('components/landing/HeroSection.tsx');
    expect(source).not.toContain('<style jsx>');
  });
});
