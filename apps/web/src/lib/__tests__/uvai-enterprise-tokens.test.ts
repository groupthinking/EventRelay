import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { UVAI_ENTERPRISE_TOKENS_CSS, uvaiEnterpriseTokensCss } from '@/lib/uvai-enterprise-tokens';

const webSrc = join(dirname(fileURLToPath(import.meta.url)), '../..');

describe('uvaiEnterpriseTokensCss', () => {
  it('does not import Node builtins (Studio client graph / next build)', () => {
    const source = readFileSync(join(webSrc, 'lib/uvai-enterprise-tokens.ts'), 'utf8');
    expect(source).not.toMatch(/from ['"]node:fs['"]/);
    expect(source).not.toMatch(/from ['"]node:path['"]/);
    expect(source).not.toMatch(/from ['"]node:url['"]/);
    expect(source).not.toMatch(/\breadFileSync\b/);
    expect(source).not.toMatch(/\bfileURLToPath\b/);
  });

  it('stays byte-identical to the stylesheet used by globals.css', () => {
    const stylesheet = readFileSync(join(webSrc, 'styles/uvai-enterprise-tokens.css'), 'utf8');
    expect(UVAI_ENTERPRISE_TOKENS_CSS).toBe(stylesheet);
    expect(uvaiEnterpriseTokensCss()).toBe(stylesheet);
    expect(uvaiEnterpriseTokensCss()).toContain('--uvai-surface: #ffffff');
    expect(uvaiEnterpriseTokensCss()).toContain('[data-pack-theme="enterprise-dark"]');
    expect(uvaiEnterpriseTokensCss()).toContain('--uvai-surface: #09090b');
  });
});
