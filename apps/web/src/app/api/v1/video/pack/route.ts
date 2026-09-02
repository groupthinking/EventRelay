import { handleIdentityPackPost } from '@/lib/video-pack';

export const runtime = 'nodejs';

export async function POST(request: Request): Promise<Response> {
  return handleIdentityPackPost(request);
}
