import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { assembleAppBuilder } from '@/lib/assemble-app-builder';
import {
  QJ_PACK_ID,
  QJ_SOP_STEPS,
  QJ_SOURCE_HASH,
  QJ_SOURCE_URL,
  QJ_TRANSCRIPT,
  QJ_VIDEO_ID,
  QJ_VISUAL_EVENTS,
} from '@/lib/__fixtures__/qj-z5ohr7sga-emit';

const created: string[] = [];

afterEach(() => {
  for (const dir of created.splice(0)) {
    rmSync(dir, { recursive: true, force: true });
  }
});

describe('assembleAppBuilder gates (QjZ5ohr7sGA)', () => {
  it(
    'materializes the Qj workspace and records real install/build/typecheck',
    async () => {
      const workspaceDir = mkdtempSync(join(tmpdir(), 'uvai-assemble-qj-'));
      created.push(workspaceDir);

      const { receipt } = await assembleAppBuilder(
        {
          videoId: QJ_VIDEO_ID,
          sourceUrl: QJ_SOURCE_URL,
          sourceHash: QJ_SOURCE_HASH,
          packId: QJ_PACK_ID,
          transcript: QJ_TRANSCRIPT,
          visualEvents: QJ_VISUAL_EVENTS,
          sopSteps: QJ_SOP_STEPS,
        },
        { workspaceDir, runGates: true },
      );

      const byName = Object.fromEntries(receipt.gates.map((gate) => [gate.name, gate]));
      expect(byName.install?.status).toBe('pass');
      expect(byName.build?.status).toBe('pass');
      expect(byName.typecheck?.status).toBe('pass');
      expect(byName.browser_smoke?.status).toBe('untested');
      expect(receipt.videoId).toBe(QJ_VIDEO_ID);
      expect(receipt.sourceHash).toBe(QJ_SOURCE_HASH);
      expect(receipt.filesDigest).toMatch(/^[a-f0-9]{64}$/);
      expect(receipt.dependencies.find((dep) => dep.name === 'typescript')?.resolved).toBe('5.7.3');
      expect(receipt.dependencies.find((dep) => dep.name === 'vite')?.resolved).toBe('6.4.3');
      expect(receipt.claims.recreates_demonstrated_app).toBe(false);
      expect(receipt.claims.live_deploy_url).toBe(false);
      expect(receipt.claims.gate_studio_deploy).toBe(false);
      expect(receipt.assembledAt).toMatch(/^\d{4}-\d{2}-\d{2}T/);

      const written = JSON.parse(readFileSync(join(workspaceDir, 'assembly.receipt.json'), 'utf8')) as {
        filesDigest: string;
        gates: Array<{ name: string; status: string }>;
      };
      expect(written.filesDigest).toBe(receipt.filesDigest);
      expect(written.gates.map((gate) => ({ name: gate.name, status: gate.status }))).toEqual(
        receipt.gates.map((gate) => ({ name: gate.name, status: gate.status })),
      );
    },
    180_000,
  );
});
