import { NextResponse } from 'next/server';
import {
  evaluateHostedSpecHealth,
  factoryDeliverFromHostedSpec,
  hostedSpecHealthFromPackResolution,
  hostedSpecHealthHistory,
  hostedSpecLivePath,
  recordHostedSpecHealthCheck,
  type HostedPackResolution,
} from '@/lib/compiled-spec-host';
import { sandboxFromVideoPack } from '@/lib/emit-app-builder-sandbox';
import { buildIdentityPack, isIdentityOnlyPack } from '@/lib/video-pack';
import { getPackRecord } from '@/lib/video-pack-store';

export const runtime = 'nodejs';
export const maxDuration = 30;

type RouteContext = {
  params: Promise<{
    videoId: string;
    asset?: string[];
  }>;
};

function contentType(path: string): string {
  if (path.endsWith('.html')) return 'text/html; charset=utf-8';
  if (path.endsWith('.css')) return 'text/css; charset=utf-8';
  if (path.endsWith('.json')) return 'application/json; charset=utf-8';
  if (path.endsWith('.js') || path.endsWith('.mjs') || path.endsWith('.ts')) {
    return 'application/javascript; charset=utf-8';
  }
  if (path.endsWith('.md')) return 'text/markdown; charset=utf-8';
  if (path.endsWith('.sh')) return 'text/x-shellscript; charset=utf-8';
  return 'text/plain; charset=utf-8';
}

async function transpileTypeScript(source: string, filename: string): Promise<string> {
  try {
    const ts = await import('typescript');
    return ts.transpileModule(source, {
      compilerOptions: {
        module: ts.ModuleKind.ESNext,
        target: ts.ScriptTarget.ES2022,
      },
      fileName: filename,
    }).outputText;
  } catch {
    return source;
  }
}

function rewriteHostedIndex(html: string, videoId: string): string {
  const base = hostedSpecLivePath(videoId);
  return html
    .replace('href="/src/styles.css"', `href="${base}/src/styles.css"`)
    .replace('src="/src/main.ts"', `src="${base}/src/main.ts"`);
}

async function resolveHostedPack(videoId: string): Promise<HostedPackResolution> {
  const id = videoId.trim();
  if (!id) {
    return { kind: 'missing' };
  }
  const identity = buildIdentityPack(id);
  const record = await getPackRecord(identity.provenance.source_hash);
  if (!record) {
    return { kind: 'missing' };
  }
  if (record.state === 'processing') {
    return { kind: 'processing' };
  }
  if (record.state === 'error') {
    return { kind: 'extract_error', message: record.error };
  }
  if (isIdentityOnlyPack(record.pack)) {
    return { kind: 'identity_only' };
  }
  const sandbox = sandboxFromVideoPack(record.pack);
  return { kind: 'ready', files: sandbox.files };
}

function resolutionHttpError(resolution: HostedPackResolution): { status: number; error: string } | null {
  switch (resolution.kind) {
    case 'ready':
      return null;
    case 'missing':
      return { status: 404, error: 'Video pack not found. Generate /api/video/pack first.' };
    case 'processing':
      return { status: 202, error: 'Video pack is still processing.' };
    case 'extract_error':
      return { status: 503, error: resolution.message };
    case 'identity_only':
      return { status: 503, error: 'Compiled spec is unavailable for identity-only packs.' };
    default: {
      const unexpected: never = resolution;
      return { status: 500, error: `Unhandled pack resolution: ${JSON.stringify(unexpected)}` };
    }
  }
}

function normalizeAssetPath(assetPath: string, files: Record<string, string>): string {
  if (typeof files[assetPath] === 'string') {
    return assetPath;
  }
  if (assetPath === 'src/pack' && typeof files['src/pack.ts'] === 'string') {
    return 'src/pack.ts';
  }
  if (assetPath === 'src/pack.js' && typeof files['src/pack.ts'] === 'string') {
    return 'src/pack.ts';
  }
  return assetPath;
}

function hostedHealthJsonResponse(
  request: Request,
  videoId: string,
  resolution: HostedPackResolution,
): NextResponse {
  const health =
    resolution.kind === 'ready'
      ? recordHostedSpecHealthCheck(videoId, evaluateHostedSpecHealth(resolution.files))
      : recordHostedSpecHealthCheck(videoId, hostedSpecHealthFromPackResolution(resolution));
  const requestUrl = new URL(request.url);
  const livePath = hostedSpecLivePath(videoId);
  const liveUrl = `${requestUrl.origin}${livePath}`;
  const factoryDeliver = factoryDeliverFromHostedSpec({
    videoId,
    liveUrl,
    health,
  });
  return NextResponse.json({
    videoId,
    live_url: livePath,
    health,
    checks_recorded: hostedSpecHealthHistory(videoId).length,
    factory_deliver: factoryDeliver,
  });
}

export async function GET(request: Request, context: RouteContext): Promise<Response> {
  const { videoId, asset } = await context.params;
  const id = (videoId || '').trim();
  const parts = (asset ?? []).filter(Boolean);

  if (!id) {
    return NextResponse.json({ error: 'videoId is required', videoId: id }, { status: 400 });
  }

  if (parts.some((part) => part === '.' || part === '..')) {
    return NextResponse.json({ error: 'Invalid asset path', videoId: id }, { status: 400 });
  }

  const resolution = await resolveHostedPack(id);

  if (parts.length === 1 && parts[0] === 'health') {
    return hostedHealthJsonResponse(request, id, resolution);
  }

  if (resolution.kind !== 'ready') {
    const err = resolutionHttpError(resolution);
    if (err) {
      return NextResponse.json({ error: err.error, videoId: id }, { status: err.status });
    }
  }

  const files = resolution.kind === 'ready' ? resolution.files : {};

  const assetPath = parts.length > 0 ? parts.join('/') : 'index.html';
  const resolvedPath = normalizeAssetPath(assetPath, files);
  let body = files[resolvedPath];
  if (typeof body !== 'string') {
    return NextResponse.json({ error: `Asset not found: ${assetPath}`, videoId: id }, { status: 404 });
  }

  if (resolvedPath === 'index.html') {
    body = rewriteHostedIndex(body, id);
  } else if (resolvedPath.endsWith('.ts')) {
    body = await transpileTypeScript(body, resolvedPath);
  }

  return new Response(body, {
    status: 200,
    headers: {
      'content-type': contentType(resolvedPath),
      'cache-control': 'no-store',
    },
  });
}
