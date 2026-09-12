import { describe, it, expect } from 'vitest';
import { GET } from '@/app/api/docs/route';

describe('GET /api/docs', () => {
  it('redirects to /docs/api with a 308 status', () => {
    const req = new Request('http://localhost:3000/api/docs');
    const res = GET(req);

    expect(res.status).toBe(308);
    expect(res.headers.get('location')).toBe('http://localhost:3000/docs/api');
  });
});
