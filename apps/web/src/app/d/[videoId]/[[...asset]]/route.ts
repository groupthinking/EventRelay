import { reasonEnvelope, reasonEnvelopeJson } from '@/lib/api-reason-envelope';
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
import {
  getPackRecordWithMeta,
  getPackStoreSignal,
  type PackStoreSignal,
} from '@/lib/video-pack-store';

import { NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const maxDuration = 30;

function logHostedSpecEvent(payload: Record<string, unknown>): void {
  console.log(JSON.stringify({ scope: 'hosted-spec', ...payload }));
}

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

async function resolveHostedPack(
  videoId: string,
): Promise<{ resolution: HostedPackResolution; store: PackStoreSignal }> {
  const id = videoId.trim();
  const store = await getPackStoreSignal();
  if (!id) {
    return { resolution: { kind: 'missing' }, store };
  }
  const identity = buildIdentityPack(id);
  const lookup = await getPackRecordWithMeta(identity.provenance.source_hash);
  const storeSignal = lookup.store;

  if (lookup.outcome === 'store_error') {
    return {
      resolution: {
        kind: 'store_error',
        message: lookup.error || 'Video pack store read failed.',
      },
      store: storeSignal,
    };
  }
  if (lookup.outcome === 'miss') {
    return { resolution: { kind: 'missing' }, store: storeSignal };
  }

  const record = lookup.record;
  if (record.state === 'processing') {
    return { resolution: { kind: 'processing' }, store: storeSignal };
  }
  if (record.state === 'error') {
    return {
      resolution: { kind: 'extract_error', message: record.error },
      store: storeSignal,
    };
  }
  if (isIdentityOnlyPack(record.pack)) {
    return { resolution: { kind: 'identity_only' }, store: storeSignal };
  }
  const sandbox = sandboxFromVideoPack(record.pack);
  return { resolution: { kind: 'ready', files: sandbox.files }, store: storeSignal };
}

async function resolveHostedPackSafe(
  videoId: string,
): Promise<{ resolution: HostedPackResolution; store: PackStoreSignal }> {
  const started = Date.now();
  try {
    const result = await resolveHostedPack(videoId);
    const health = hostedSpecHealthFromPackResolution(result.resolution);
    logHostedSpecEvent({
      event: 'pack_resolve',
      videoId: videoId.trim(),
      reason_code: health.reason_code,
      resolution_kind: result.resolution.kind,
      store_backend: result.store.backend,
      store_ok: result.store.ok,
      duration_ms: Date.now() - started,
    });
    return result;
  } catch (error) {
    console.error('[hosted-spec] resolveHostedPack failed:', error);
    const resolution = hostedPackResolutionFromThrownError(error);
    const store = await getPackStoreSignal();
    const health = hostedSpecHealthFromPackResolution(resolution);
    logHostedSpecEvent({
      event: 'pack_resolve',
      videoId: videoId.trim(),
      reason_code: health.reason_code,
      resolution_kind: resolution.kind,
      store_backend: store.backend,
      store_ok: store.ok,
      duration_ms: Date.now() - started,
    });
    return { resolution, store };
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
  store: PackStoreSignal,
): NextResponse {
  const started = Date.now();
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
  logHostedSpecEvent({
    event: 'health',
    videoId: videoId.trim(),
    reason_code: health.reason_code,
    health_ok: health.ok,
    store_backend: store.backend,
    store_ok: store.ok,
    duration_ms: Date.now() - started,
  });
  return NextResponse.json(
    reasonEnvelopeJson(
      reasonEnvelope(
        health.ok,
        health.reason_code ?? 'HOSTED_SPEC_INCOMPLETE',
        health.detail,
      ),
      {
        videoId,
        live_url: livePath,
        health,
        store,
        checks_recorded: hostedSpecHealthHistory(videoId).length,
        factory_deliver: factoryDeliver,
      },
    ),
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
  const handlerStarted = Date.now();
  try {
    const { videoId, asset } = await context.params;
    const id = (videoId || '').trim();
    const parts = (asset ?? []).filter(Boolean);

    if (!id) {
      return NextResponse.json(
        reasonEnvelopeJson(reasonEnvelope(false, 'HOSTED_VIDEO_ID_REQUIRED', 'videoId is required'), {
          videoId: id,
        }),
        { status: 400 },
      );
    }

    if (parts.some((part) => part === '.' || part === '..')) {
      return NextResponse.json(
        reasonEnvelopeJson(reasonEnvelope(false, 'HOSTED_ASSET_PATH_INVALID', 'Invalid asset path'), {
          videoId: id,
        }),
        { status: 400 },
      );
    }

    const healthRequest = isHealthAssetRequest(request, id, parts);

    let resolution: HostedPackResolution;
    let store: PackStoreSignal;
    try {
      const resolved = await resolveHostedPackSafe(id);
      resolution = resolved.resolution;
      store = resolved.store;
    } catch (error) {
      console.error('[hosted-spec] unexpected resolve failure:', error);
      resolution = hostedPackResolutionFromThrownError(error);
      store = await getPackStoreSignal();
    }

    if (healthRequest) {
      return hostedHealthJsonResponse(request, id, resolution, store);
    }

    if (resolution.kind !== 'ready') {
      logHostedSpecEvent({
        event: 'html_unavailable',
        videoId: id,
        reason_code: hostedSpecHealthFromPackResolution(resolution).reason_code,
        resolution_kind: resolution.kind,
        store_backend: store.backend,
        duration_ms: Date.now() - handlerStarted,
      });
      return hostedNotReadyResponse(request, id, resolution, parts);
    }

    const files = resolution.files;
    const assetPath = parts.length > 0 ? parts.join('/') : 'index.html';
    const resolvedPath = normalizeAssetPath(assetPath, files);
    let body = files[resolvedPath];
    if (typeof body !== 'string') {
      const health = evaluateHostedSpecHealth(files);
      return NextResponse.json(
        reasonEnvelopeJson(
          reasonEnvelope(
            false,
            health.reason_code ?? 'HOSTED_SPEC_INCOMPLETE',
            health.detail ?? `Asset not found: ${assetPath}`,
          ),
          { videoId: id },
        ),
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
    const store = await getPackStoreSignal();
    if (isHealthAssetRequest(request, id, parts)) {
      return hostedHealthJsonResponse(request, id, resolution, store);
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
