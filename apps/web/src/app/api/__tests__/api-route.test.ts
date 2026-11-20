import { describe, expect, it } from 'vitest';
import { GET } from '@/app/api/route';

describe('GET /api', () => {
  it('names the UVAI API and records that pipeline routes are retired', async () => {
    const response = await GET();
    const body = await response.json();

    expect(body.name).toBe('UVAI API');
    expect(body.endpoints.video).toBeUndefined();
    expect(body.endpoints.pipeline).toContain('retired');
  });
});
