import { NextResponse } from 'next/server';
import {
  evaluateHostedSpecHealth,
  factoryDeliverFromHostedSpec,
  hostedSpecHealthHistory,
  hostedSpecLivePath,
  recordHostedSpecHealthCheck,
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

async function resolveHostedFiles(videoId: string): Promise<
  | { ok: true; files: Record<string, string> }
  | { ok: false; status: number; error: string }
> {
  const id = videoId.trim();
  if (!id) {
    return { ok: false, status: 400, error: 'videoId is required' };
  }
  const identity = buildIdentityPack(id);
  const record = await getPackRecord(identity.provenance.source_hash);
  if (!record) {
    return { ok: false, status: 404, error: 'Video pack not found. Generate /api/video/pack first.' };
  }
  if (record.state === 'processing') {
    return { ok: false, status: 202, error: 'Video pack is still processing.' };
  }
  if (record.state === 'error') {
    return { ok: false, status: 503, error: record.error };
  }
  if (isIdentityOnlyPack(record.pack)) {
    return { ok: false, status: 503, error: 'Compiled spec is unavailable for identity-only packs.' };
  }
  const sandbox = sandboxFromVideoPack(record.pack);
  return { ok: true, files: sandbox.files };
}

export async function GET(request: Request, context: RouteContext): Promise<Response> {
  const { videoId, asset } = await context.params;
  const id = (videoId || '').trim();
  const resolved = await resolveHostedFiles(id);
  if (!resolved.ok) {
    return NextResponse.json({ error: resolved.error, videoId: id }, { status: resolved.status });
  }

  const parts = (asset ?? []).filter(Boolean);
  if (parts.some((part) => part === '.' || part === '..')) {
    return NextResponse.json({ error: 'Invalid asset path', videoId: id }, { status: 400 });
  }

  if (parts.length === 1 && parts[0] === 'health') {
    const health = recordHostedSpecHealthCheck(id, evaluateHostedSpecHealth(resolved.files));
    const requestUrl = new URL(request.url);
    const livePath = hostedSpecLivePath(id);
    const liveUrl = `${requestUrl.origin}${livePath}`;
    const factoryDeliver = factoryDeliverFromHostedSpec({
      videoId: id,
      liveUrl,
      health,
    });
    return NextResponse.json({
      videoId: id,
      live_url: livePath,
      health,
      checks_recorded: hostedSpecHealthHistory(id).length,
      factory_deliver: factoryDeliver,
    });
  }

  const assetPath = parts.length > 0 ? parts.join('/') : 'index.html';
  let body = resolved.files[assetPath];
  if (typeof body !== 'string') {
    return NextResponse.json({ error: `Asset not found: ${assetPath}`, videoId: id }, { status: 404 });
  }

  if (assetPath === 'index.html') {
    body = rewriteHostedIndex(body, id);
  } else if (assetPath.endsWith('.ts')) {
    body = await transpileTypeScript(body, assetPath);
  }

  return new Response(body, {
    status: 200,
    headers: {
      'content-type': contentType(assetPath),
      'cache-control': 'no-store',
    },
  });
}
