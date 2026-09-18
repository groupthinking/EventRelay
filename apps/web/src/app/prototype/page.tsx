import { redirect } from 'next/navigation';
import { CANONICAL_STUDIO_PATH } from '@/lib/auth-paths';

/**
 * The former route was an interactive simulation that could be mistaken for a
 * verified workflow. Keep old bookmarks working while routing users to the
 * canonical OneLoopStudio workbench.
 */
export default function PrototypeRedirect() {
  redirect(CANONICAL_STUDIO_PATH);
}
