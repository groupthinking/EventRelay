import { createChat, listChats } from '@/lib/studio/routes';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 120;
export const GET = listChats;
export const POST = createChat;
