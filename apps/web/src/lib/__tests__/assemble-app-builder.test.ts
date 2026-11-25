import { describe, expect, it } from 'vitest';
import { identityHash } from '@/lib/video-pack';
import { APP_BUILDER_PINNED_DEPS, emitAppBuilderSandbox } from '@/lib/emit-app-builder-sandbox';
import { assembleAppBuilder, planAssembly } from '@/lib/assemble-app-builder';
import {
  QJ_FORBIDDEN_ARCHITECTURE,
  QJ_FORBIDDEN_CODE_SNIPPETS,
  QJ_PACK_ID,
  QJ_SOP_STEPS,
  QJ_SOURCE_HASH,
  QJ_SOURCE_URL,
  QJ_TRANSCRIPT,
  QJ_VIDEO_ID,
  QJ_VISUAL_EVENTS,
} from '@/lib/__fixtures__/qj-z5ohr7sga-emit';
import {
  XYMC_PACK_ID,
  XYMC_SOP_STEPS,
  XYMC_SOURCE_HASH,
  XYMC_SOURCE_URL,
  XYMC_TRANSCRIPT,
  XYMC_VIDEO_ID,
  XYMC_VISUAL_EVENTS,
} from '@/lib/__fixtures__/xymcbrfsj4c-emit';

const SOURCE_FILE_HASH = /^[a-f0-9]{64}$/;

function qjInput() {
  return {
    videoId: QJ_VIDEO_ID,
    sourceUrl: QJ_SOURCE_URL,
    sourceHash: QJ_SOURCE_HASH,
    packId: QJ_PACK_ID,
    transcript: QJ_TRANSCRIPT,
    visualEvents: QJ_VISUAL_EVENTS,
    sopSteps: QJ_SOP_STEPS,
  };
}

function xymcInput() {
  return {
    videoId: XYMC_VIDEO_ID,
    sourceUrl: XYMC_SOURCE_URL,
    sourceHash: XYMC_SOURCE_HASH,
    packId: XYMC_PACK_ID,
    transcript: XYMC_TRANSCRIPT,
    visualEvents: [...XYMC_VISUAL_EVENTS],
    sopSteps: [...XYMC_SOP_STEPS],
  };
}

describe('planAssembly (identity receipt)', () => {
  it('uses the live QjZ5ohr7sGA identity and a deterministic filesDigest', () => {
    expect(identityHash(QJ_VIDEO_ID)).toBe(QJ_SOURCE_HASH);
    const sandbox = emitAppBuilderSandbox(qjInput());
    const first = planAssembly(sandbox);
    const second = planAssembly(emitAppBuilderSandbox(qjInput()));
    expect(first.contract).toBe('app-builder-assembly');
    expect(first.videoId).toBe(QJ_VIDEO_ID);
    expect(first.sourceHash).toBe(QJ_SOURCE_HASH);
    expect(first.packId).toBe(QJ_PACK_ID);
    expect(first.filesDigest).toMatch(/^[a-f0-9]{64}$/);
    expect(first.identityDigest).toMatch(/^[a-f0-9]{64}$/);
    expect(first.filesDigest).toBe(second.filesDigest);
    expect(first.identityDigest).toBe(second.identityDigest);
    expect(first.assembledAt).toBeNull();
    expect(first.workspaceDir).toBeNull();
  });

  it('keeps QjZ5ohr7sGA and XYMcBrFSJ4c assembly identities distinct', () => {
    const qj = planAssembly(emitAppBuilderSandbox(qjInput()));
    const xymc = planAssembly(emitAppBuilderSandbox(xymcInput()));
    expect(qj.videoId).not.toBe(xymc.videoId);
    expect(qj.sourceHash).not.toBe(xymc.sourceHash);
    expect(qj.filesDigest).not.toBe(xymc.filesDigest);
    expect(qj.identityDigest).not.toBe(xymc.identityDigest);
    expect(qj.files.some((file) => file.path === 'index.html')).toBe(true);
    expect(xymc.files.some((file) => file.path === 'index.html')).toBe(true);
  });

  it('pins typescript and vite exactly and never marks claims true', () => {
    const receipt = planAssembly(emitAppBuilderSandbox(qjInput()));
    expect(receipt.dependencies).toEqual([
      { name: 'typescript', pinned: APP_BUILDER_PINNED_DEPS.typescript, resolved: null },
      { name: 'vite', pinned: APP_BUILDER_PINNED_DEPS.vite, resolved: null },
    ]);
    expect(receipt.claims).toEqual({
      recreates_demonstrated_app: false,
      live_deploy_url: false,
      gate_studio_deploy: false,
      credentials_embedded: false,
    });
    expect(receipt.gates.every((gate) => gate.status === 'untested')).toBe(true);
    expect(receipt.gates.map((gate) => gate.name)).toEqual([
      'install',
      'build',
      'typecheck',
      'browser_smoke',
    ]);
  });

  it('labels Qj as a viewer with no named automation integrations', () => {
    const receipt = planAssembly(emitAppBuilderSandbox(qjInput()));
    const ids = receipt.unresolved.map((row) => row.id);
    expect(ids).toContain('viewer-not-recreation');
    expect(ids).toContain('architecture-stripped');
    expect(ids).toContain('no-live-deploy');
    expect(ids).toContain('gate-parked');
    expect(ids).toContain('sop-checklist-local-only');
    expect(ids).toContain('browser-smoke-untested');
    expect(ids).toContain('no-external-credentials');
    expect(ids.some((id) => id.startsWith('unsupported:'))).toBe(false);
    expect(receipt.unresolved.every((row) => row.kind !== 'unsupported_capability' || row.id === 'architecture-stripped' || row.id === 'no-live-deploy' || row.id === 'gate-parked')).toBe(true);
  });

  it('labels XYMc named automations as unsupported instead of implemented', () => {
    const receipt = planAssembly(emitAppBuilderSandbox(xymcInput()));
    const ids = receipt.unresolved.map((row) => row.id);
    expect(ids).toContain('unsupported:n8n');
    expect(ids).toContain('unsupported:make');
    expect(ids).toContain('unsupported:retell');
    expect(ids).toContain('unsupported:voiceflow');
    expect(ids).toContain('unsupported:telegram');
    expect(ids).toContain('unsupported:stripe');
    expect(ids).toContain('unsupported:twilio');
    expect(ids).toContain('missing-provider-credentials');
    expect(ids).not.toContain('no-external-credentials');
    expect(receipt.claims.recreates_demonstrated_app).toBe(false);
  });

  it('does not invent architecture or code snippets into the file list', async () => {
    const { sandbox, receipt } = await assembleAppBuilder(qjInput());
    const shipped = Object.values(sandbox.files).join('\n');
    expect(shipped).toContain('Safety and Vehicle Staging');
    expect(shipped).toContain('data-testid="sop-check"');
    expect(shipped).toContain('data-testid="assembly-honesty"');
    expect(shipped).not.toContain(QJ_FORBIDDEN_ARCHITECTURE.summary);
    expect(shipped).not.toContain('tire_procedure.ts');
    expect(shipped).not.toContain('TireChangeContext');
    expect(shipped).not.toContain(QJ_FORBIDDEN_CODE_SNIPPETS[0]?.content ?? 'missing');
    expect(receipt.files.map((file) => file.path).join('\n')).not.toContain('tire_procedure.ts');
    expect(receipt.files.every((file) => SOURCE_FILE_HASH.test(file.sha256))).toBe(true);
  });
});
