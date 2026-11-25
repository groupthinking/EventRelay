import { handleIdentityPackGet, handleIdentityPackPost } from '@/lib/video-pack';

export const runtime = 'nodejs';
export const maxDuration = 120;

export async function POST(request: Request): Promise<Response> {
  return handleIdentityPackPost(request);
}

export async function GET(request: Request): Promise<Response> {
  return handleIdentityPackGet(request);
}
