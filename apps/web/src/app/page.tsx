import { redirect } from 'next/navigation';

/** Primary product entry: unified dashboard journey (see /studio for legacy local drafts). */
export default function Home() {
  redirect('/dashboard');
}