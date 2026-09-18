import { NextResponse } from 'next/server';
import { handleAppBuilderSandboxGet, handleAppBuilderSandboxPost } from '@/lib/app-builder-sandbox-route';
import { isAppBuilderSandbox, planAssembly } from '@/lib/assemble-app-builder';

function isSuccessSandboxBody(body: unknown): body is { status: 'success'; data: unknown } {
  if (body === null || typeof body !== 'object') return false;
  const row = body as { status?: unknown; data?: unknown };
  return row.status === 'success';
}

async function attachAssembly(response: Response): Promise<NextResponse> {
  const status = response.status;
  let body: unknown;
  try {
    body = await response.json();
  } catch (error) {
    console.error('assemble: sandbox response was not JSON', error);
    return NextResponse.json(
      { status: 'error', error: 'Sandbox lookup returned a non-JSON body.' },
      { status: 502 },
    );
  }

  if (status !== 200 || !isSuccessSandboxBody(body) || !isAppBuilderSandbox(body.data)) {
    return NextResponse.json(body, { status });
  }

  const assembly = planAssembly(body.data);
  return NextResponse.json({
    status: 'success',
    data: {
      ...body.data,
      assembly,
    },
  });
}

export async function handleAppBuilderAssembleGet(request: Request): Promise<Response> {
  return attachAssembly(await handleAppBuilderSandboxGet(request));
}

export async function handleAppBuilderAssemblePost(request: Request): Promise<Response> {
  return attachAssembly(await handleAppBuilderSandboxPost(request));
}
