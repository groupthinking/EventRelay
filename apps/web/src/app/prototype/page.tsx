import { redirect } from 'next/navigation';

/**
 * The former route was an interactive simulation that could be mistaken for a
 * verified workflow. Keep old bookmarks working while routing users to the
 * real evidence-gated dashboard.
 */
export default function PrototypeRedirect() {
  redirect('/dashboard');
}
