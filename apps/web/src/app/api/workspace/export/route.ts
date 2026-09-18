import { NextResponse } from 'next/server';
import { applyVerifiedBillingCookie, requireProFeatureAccess } from '@/lib/billing/pro-feature-gate';
import { studioExportFilename } from '@/lib/studio-pipeline-status';
import { zipUtf8Files } from '@/lib/zip-store';

export const runtime = 'nodejs';

type WorkspaceExportRequest = {
  projectName?: string;
  files?: Record<string, string>;
  sessionId?: string;
};

function normalizeFiles(files: WorkspaceExportRequest['files']): Record<string, string> | null {
  if (!files || typeof files !== 'object') return null;

  const normalized: Record<string, string> = {};
  for (const [path, content] of Object.entries(files)) {
    if (typeof content !== 'string') return null;
    const trimmedPath = path.trim().replace(/\\/g, '/');
    if (!trimmedPath || trimmedPath.startsWith('/')) return null;
    if (trimmedPath.split('/').some((part) => !part || part === '.' || part === '..')) return null;
    normalized[trimmedPath] = content;
  }

  return Object.keys(normalized).length > 0 ? normalized : null;
}

function quotedFilename(filename: string): string {
  return filename.replace(/"/g, '');
}

export async function POST(request: Request) {
  let body: WorkspaceExportRequest;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'invalid_json', code: 'invalid_json' }, { status: 400 });
  }

  const files = normalizeFiles(body.files);
  if (!files) {
    return NextResponse.json(
      { error: 'files_required', code: 'files_required' },
      { status: 400 },
    );
  }

  const access = await requireProFeatureAccess(request, {
    featureKey: 'workspace_export',
    featureLabel: 'Workspace ZIP exports',
    sessionId: body.sessionId,
  });
  if (!access.ok) {
    return access.response;
  }

  const filename = studioExportFilename(body.projectName);
  const zip = zipUtf8Files(files);
  const response = new NextResponse(Buffer.from(zip), {
    status: 200,
    headers: {
      'cache-control': 'no-store',
      'content-disposition': `attachment; filename="${quotedFilename(filename)}"`,
      'content-length': String(zip.byteLength),
      'content-type': 'application/zip',
    },
  });
  applyVerifiedBillingCookie(response, access.signedBillingEmail);
  return response;
}
