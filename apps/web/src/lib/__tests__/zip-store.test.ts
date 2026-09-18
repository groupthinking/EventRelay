import { describe, expect, it } from 'vitest';
import { zipEntryNames, zipUtf8Files } from '@/lib/zip-store';

describe('zipUtf8Files', () => {
  it('packs UTF-8 files into a store zip Chrome can save as one download', () => {
    const zip = zipUtf8Files({
      'SHOPIFY.md': 'npm init @shopify/app@latest',
      'app/page.tsx': 'export default function Page() { return null; }',
    });
    expect(zip[0]).toBe(0x50);
    expect(zip[1]).toBe(0x4b);
    expect(zipEntryNames(zip)).toEqual(['SHOPIFY.md', 'app/page.tsx']);
    expect(new TextDecoder().decode(zip)).toContain('shopify/app');
  });
});
