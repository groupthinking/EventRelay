import { listMessages, sendMessage } from '@/lib/studio/routes';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 300;
export const GET = listMessages;
export const POST = sendMessage;
