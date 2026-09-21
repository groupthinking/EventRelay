import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { UVAI_ENTERPRISE_TOKENS_CSS } from '@/lib/uvai-enterprise-tokens';

describe('uvai-enterprise-tokens drift guard', () => {
  it('TS const matches the shared CSS file (minus header comment)', () => {
    const here = dirname(fileURLToPath(import.meta.url));
    const cssFile = readFileSync(join(here, '../../styles/uvai-enterprise-tokens.css'), 'utf-8');
    const withoutHeader = cssFile.replace(/^\/\*\*[\s\S]*?\*\/\s*/, '');
    expect(withoutHeader.trim()).toBe(UVAI_ENTERPRISE_TOKENS_CSS.trim());
  });

  it('stays client-safe: no node imports in the tokens module', () => {
    const here = dirname(fileURLToPath(import.meta.url));
    const source = readFileSync(join(here, '../uvai-enterprise-tokens.ts'), 'utf-8');
    expect(source).not.toMatch(/from\s+['"]node:/);
    expect(source).not.toMatch(/require\(\s*['"]node:/);
  });
});
