import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

let cachedTokensCss: string | undefined;

/** Enterprise design tokens CSS block (issue #2197 P0). */
export function uvaiEnterpriseTokensCss(): string {
  if (cachedTokensCss === undefined) {
    const here = dirname(fileURLToPath(import.meta.url));
    cachedTokensCss = readFileSync(join(here, '../styles/uvai-enterprise-tokens.css'), 'utf-8');
  }
  return cachedTokensCss;
}
