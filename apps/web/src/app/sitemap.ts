import type { MetadataRoute } from 'next';

const BASE = 'https://uvai.io';

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  const routes = ['', '/dashboard', '/pricing', '/features', '/playground'];
  return routes.map((path) => ({
    url: `${BASE}${path}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: path === '' ? 1.0 : 0.7,
  }));
}
