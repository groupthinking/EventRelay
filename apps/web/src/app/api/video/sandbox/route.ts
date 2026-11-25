import {
  handleAppBuilderSandboxGet,
  handleAppBuilderSandboxPost,
} from '@/lib/app-builder-sandbox-route';

export const runtime = 'nodejs';
export const maxDuration = 30;

export async function POST(request: Request): Promise<Response> {
  return handleAppBuilderSandboxPost(request);
}

export async function GET(request: Request): Promise<Response> {
  return handleAppBuilderSandboxGet(request);
}
