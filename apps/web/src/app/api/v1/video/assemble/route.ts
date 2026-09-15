import {
  handleAppBuilderAssembleGet,
  handleAppBuilderAssemblePost,
} from '@/lib/assemble-app-builder-route';

export const runtime = 'nodejs';
export const maxDuration = 30;

export async function POST(request: Request): Promise<Response> {
  return handleAppBuilderAssemblePost(request);
}

export async function GET(request: Request): Promise<Response> {
  return handleAppBuilderAssembleGet(request);
}
