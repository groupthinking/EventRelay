import { describe, expect, it } from 'vitest';
import { GET } from '@/app/api/route';

describe('GET /api', () => {
  it('identifies deprecated video and retired pipeline routes', async () => {
    const response = await GET();
    const body = await response.json();

    expect(body.endpoints.video).toContain('DEPRECATED');
    expect(body.endpoints.pipeline).toContain('retired');
  });
});
