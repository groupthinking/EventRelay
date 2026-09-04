import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { canonicalStudioPath } from '@/lib/auth-paths';

export const metadata: Metadata = {
  title: 'Studio',
  description: 'Redirect to the UVAI workbench.',
  alternates: { canonical: '/' },
  robots: { index: false, follow: true },
};

export default async function LegacyDashboardRedirect({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (typeof value === 'string' && value.length > 0) {
      qs.set(key, value);
    } else if (Array.isArray(value) && value[0]) {
      qs.set(key, value[0]);
    }
  }
  const suffix = qs.toString();
  redirect(canonicalStudioPath(suffix ? `?${suffix}` : ''));
}
