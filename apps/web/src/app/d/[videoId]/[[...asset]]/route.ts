import { NextResponse } from 'next/server';
import {
  evaluateHostedSpecHealth,
  factoryDeliverFromHostedSpec,
  hostedPackAssetUnavailableJson,
  hostedPackResolutionFromThrownError,
  hostedSpecHealthFromPackResolution,
  hostedSpecHealthHistory,
  hostedSpecLivePath,
  hostedLivePageUnavailableResponse,
  isHostedHealthPath,
  isHostedLivePageRequest,
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

async function resolveHostedPackSafe(videoId: string): Promise<HostedPackResolution> {
  try {
    return await resolveHostedPack(videoId);
  } catch (error) {
    console.error('[hosted-spec] resolveHostedPack failed:', error);
    return hostedPackResolutionFromThrownError(error);
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
  if (assetPath === 'src/pack.ts' && typeof files['src/pack.ts'] === 'string') {
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
  return NextResponse.json(
    {
      videoId,
      live_url: livePath,
      health,
      checks_recorded: hostedSpecHealthHistory(videoId).length,
      factory_deliver: factoryDeliver,
    },
    { status: 200 },
  );
}

function hostedNotReadyResponse(
  request: Request,
  videoId: string,
  resolution: HostedPackResolution,
  assetParts: string[],
): Response {
  if (isHostedLivePageRequest(request, videoId, assetParts)) {
    return hostedLivePageUnavailableResponse(videoId, resolution);
  }
  const health = hostedSpecHealthFromPackResolution(resolution);
  const status = resolution.kind === 'processing' ? 202 : 404;
  return NextResponse.json(hostedPackAssetUnavailableJson(videoId, health), {
    status,
    headers: { 'cache-control': 'no-store' },
  });
}

function isHealthAssetRequest(request: Request, videoId: string, assetParts: string[]): boolean {
  if (assetParts.length === 1 && assetParts[0]?.toLowerCase() === 'health') {
    return true;
  }
  try {
    return isHostedHealthPath(new URL(request.url).pathname, videoId);
  } catch {
    return false;
  }
}

export async function GET(request: Request, context: RouteContext): Promise<Response> {
  try {
    const { videoId, asset } = await context.params;
    const id = (videoId || '').trim();
    const parts = (asset ?? []).filter(Boolean);

    if (!id) {
      return NextResponse.json({ error: 'videoId is required', videoId: id }, { status: 400 });
    }

    if (parts.some((part) => part === '.' || part === '..')) {
      return NextResponse.json({ error: 'Invalid asset path', videoId: id }, { status: 400 });
    }

    const healthRequest = isHealthAssetRequest(request, id, parts);

    let resolution: HostedPackResolution;
    try {
      resolution = await resolveHostedPackSafe(id);
    } catch (error) {
      console.error('[hosted-spec] unexpected resolve failure:', error);
      resolution = hostedPackResolutionFromThrownError(error);
    }

    if (healthRequest) {
      return hostedHealthJsonResponse(request, id, resolution);
    }

    if (resolution.kind !== 'ready') {
      return hostedNotReadyResponse(request, id, resolution, parts);
    }

    const files = resolution.files;
    const assetPath = parts.length > 0 ? parts.join('/') : 'index.html';
    const resolvedPath = normalizeAssetPath(assetPath, files);
    let body = files[resolvedPath];
    if (typeof body !== 'string') {
      const health = evaluateHostedSpecHealth(files);
      return NextResponse.json(
        {
          videoId: id,
          error: `Asset not found: ${assetPath}`,
          reason_code: health.reason_code ?? 'HOSTED_SPEC_INCOMPLETE',
          detail: health.detail,
        },
        { status: 404 },
      );
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
  } catch (error) {
    console.error('[hosted-spec] GET /d handler failed:', error);
    const { videoId, asset } = await context.params;
    const id = (videoId || '').trim();
    const parts = (asset ?? []).filter(Boolean);
    const resolution = hostedPackResolutionFromThrownError(error);
    if (isHealthAssetRequest(request, id, parts)) {
      return hostedHealthJsonResponse(request, id, resolution);
    }
    if (isHostedLivePageRequest(request, id, parts)) {
      return hostedLivePageUnavailableResponse(id, resolution);
    }
    const health = hostedSpecHealthFromPackResolution(resolution);
    return NextResponse.json(hostedPackAssetUnavailableJson(id, health), {
      status: 404,
      headers: { 'cache-control': 'no-store' },
    });
  }
}
