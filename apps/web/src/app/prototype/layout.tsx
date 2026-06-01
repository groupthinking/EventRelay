import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Prototype spec',
  description:
    'Internal prototype spec for the UVAI build flow. Not indexed.',
  robots: { index: false, follow: false, nocache: true },
};

export default function PrototypeLayout({ children }: { children: React.ReactNode }) {
  return children;
}
