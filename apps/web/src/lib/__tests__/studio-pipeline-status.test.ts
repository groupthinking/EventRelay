import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import {
  studioActActionLabel,
  studioCanExport,
  studioEventsEmptyMessage,
  studioExportOutcomeMessage,
  studioInvalidHandoffMessage,
  studioPackCitation,
  studioPackFormation,
  studioPasteOutcomeMessage,
  studioPromotePackWorkbench,
  studioRunQuality,
  studioStatusLabel,
  studioShowTranscriptRetry,
  studioStatusMessage,
  studioTranscriptStage,
  studioWorkingMessage,
} from '../studio-pipeline-status';

describe('studio-pipeline-status', () => {
  it('marks a job_id kickoff as draft until transcript or events exist', () => {
    expect(
      studioRunQuality(
        { ok: true, status: 200, pipeline: 'backend-async', jobId: 'job_1' },
        false,
        true,
      ),
    ).toBe('draft');
  });

  it('marks live when transcript or events are present', () => {
    expect(
      studioRunQuality(
        { ok: true, status: 200, pipeline: 'backend-async', jobId: 'job_1' },
        false,
        true,
        { transcript: 'x'.repeat(50), eventCount: 0 },
      ),
    ).toBe('live');
  });

  it('marks local fallback as draft', () => {
    expect(
      studioRunQuality(
        { ok: true, status: 200, pipeline: 'local-fallback' },
        false,
        true,
      ),
    ).toBe('draft');
  });

  it('uses no-transcript label when ready without payload', () => {
    expect(studioStatusLabel('draft', 'ready')).toBe('No transcript yet');
    expect(studioStatusLabel('live', 'ready')).toBe('Analysis ready');
  });

  it('shows the identity pack cite when transcript evidence is missing', () => {
    const citation = studioPackCitation({
      version: 'v0',
      videoId: 'jNQXAC9IVRw',
      packId: 'vp:v0:jNQXAC9IVRw',
      sourceUrl: 'https://www.youtube.com/watch?v=jNQXAC9IVRw',
      sourceHash: '97150a5c21eef3d12a4543ce2108ca28fd6f829db1da120d7e75655ab471f97d',
      pack: {
        version: 'v0',
        id: 'vp:v0:jNQXAC9IVRw',
        video_id: 'jNQXAC9IVRw',
        source_url: 'https://www.youtube.com/watch?v=jNQXAC9IVRw',
        provenance: {
          source_hash: '97150a5c21eef3d12a4543ce2108ca28fd6f829db1da120d7e75655ab471f97d',
        },
      },
    });
    expect(citation).toContain('cite:youtube:jNQXAC9IVRw');
    expect(citation).toContain('https://www.youtube.com/watch?v=jNQXAC9IVRw');
    expect(citation).toContain('97150a5c21eef3d12a4543ce2108ca28fd6f829db1da120d7e75655ab471f97d');
    expect(
      studioPasteOutcomeMessage({
        hasUsableTranscript: false,
        packCitation: citation,
      }),
    ).toContain('cite:youtube:jNQXAC9IVRw');
  });

  it('fails closed when paste finishes without a verified pack', () => {
    const message = studioPasteOutcomeMessage({
      hasUsableTranscript: false,
      packCitation: null,
    });
    expect(message).toMatch(/pack emit failed|verification failed/i);
    expect(message.toLowerCase()).not.toBe('no usable transcript. try another public video.');
  });

  it('does not send the user to a second product when ready', () => {
    const draft = studioStatusMessage('draft', 'ready', 'App', false);
    const live = studioStatusMessage('live', 'ready', 'App', false);
    expect(draft.toLowerCase()).not.toContain('planning draft');
    expect(live.toLowerCase()).not.toContain('dashboard');
  });

  it('binds stack checks to pack.stack.tools and keeps studio on /', () => {
    const formation = studioPackFormation({
      version: 'v0',
      videoId: 'MNNfat_QP0E',
      packId: 'vp:v0:MNNfat_QP0E',
      sourceUrl: 'https://www.youtube.com/watch?v=MNNfat_QP0E',
      sourceHash: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      pack: {
        version: 'v0',
        id: 'vp:v0:MNNfat_QP0E',
        video_id: 'MNNfat_QP0E',
        source_url: 'https://www.youtube.com/watch?v=MNNfat_QP0E',
        provenance: {
          source_hash: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
        },
        architecture: {
          summary: 'decode to rails',
          stages: [
            { id: 'decode', name: 'decode', description: 'frames' },
            { id: 'rails', name: 'monetization rails', description: 'x402' },
          ],
          mermaid: 'flowchart LR\ndecode-->rails',
        },
        artifacts: [
          {
            path_hint: 'src/mcp_x402_gateway.ts',
            purpose: 'Paid MCP gateway',
            interface: 'createGateway(config: GatewayConfig): Gateway',
          },
        ],
        stack: {
          tools: [{ name: 'Cloudflare' }, { name: 'x402' }],
        },
      },
    });
    expect(formation.tools.map((tool) => tool.name)).toEqual(['Cloudflare', 'x402']);
    expect(formation.checks.map((item) => item.title).join(' ')).not.toMatch(/shopify/i);
    expect(formation.checks.some((item) => /cloudflare|x402/i.test(item.title))).toBe(true);
    expect(formation.architecture?.stages).toHaveLength(2);
    expect(formation.artifacts[0]?.path_hint).toBe('src/mcp_x402_gateway.ts');

    const studio = readFileSync(join(process.cwd(), 'src/components/OneLoopStudio.tsx'), 'utf8');
    expect(studio).toContain('studioPackFormation');
    expect(studio).toContain('data-testid="pack-architecture"');
    expect(studio).toContain('data-testid="pack-artifacts"');
    expect(studio).not.toMatch(/router\.(push|replace)\(['"]\/dashboard/);
  });

  it('tells the truth when events[] is empty after a completed run', () => {
    expect(
      studioEventsEmptyMessage({
        busy: true,
        runStatus: 'processing',
        eventCount: 0,
        hasArchitecture: true,
        artifactCount: 2,
        toolCount: 1,
      }),
    ).toMatch(/extracting events/i);
    expect(
      studioEventsEmptyMessage({
        busy: false,
        runStatus: null,
        eventCount: 0,
        hasArchitecture: false,
        artifactCount: 0,
        toolCount: 0,
      }),
    ).toBe('Events show up after Run.');

    const emptyWithPack = studioEventsEmptyMessage({
      busy: false,
      runStatus: 'complete',
      eventCount: 0,
      hasArchitecture: true,
      artifactCount: 2,
      toolCount: 1,
    });
    expect(emptyWithPack.toLowerCase()).not.toContain('show up after run');
    expect(emptyWithPack.toLowerCase()).not.toContain('extracting');
    expect(emptyWithPack.toLowerCase()).not.toMatch(/\bbelow\b/);
    expect(emptyWithPack.toLowerCase()).toMatch(/no extracted events/);
    expect(emptyWithPack.toLowerCase()).toMatch(/architecture|artifacts|stack/);
    expect(
      studioEventsEmptyMessage({
        busy: false,
        runStatus: 'failed',
        eventCount: 0,
        hasArchitecture: false,
        artifactCount: 0,
        toolCount: 0,
      }),
    ).toMatch(/analysis failed/i);
    expect(studioPromotePackWorkbench({ eventCount: 0, hasArchitecture: true, artifactCount: 2, toolCount: 1 })).toBe(
      true,
    );
    expect(studioPromotePackWorkbench({ eventCount: 0, hasArchitecture: false, artifactCount: 0, toolCount: 2 })).toBe(
      true,
    );
    expect(studioPromotePackWorkbench({ eventCount: 3, hasArchitecture: true, artifactCount: 2, toolCount: 1 })).toBe(
      false,
    );
    expect(studioPromotePackWorkbench({ eventCount: 3, hasArchitecture: true, artifactCount: 2, toolCount: 0 })).toBe(
      true,
    );
  });

  it('shows pack progress while waiting on transcript', () => {
    expect(studioTranscriptStage({ hasPack: false, hasTranscript: false })).toBe('pack');
    expect(studioTranscriptStage({ hasPack: true, hasTranscript: false })).toBe('transcript');
    expect(studioTranscriptStage({ hasPack: true, hasTranscript: true })).toBe('analysis');
    const fetching = studioWorkingMessage({
      elapsedSec: 12,
      hasPack: false,
      hasTranscript: false,
    });
    expect(fetching).toMatch(/1\/3 pack/i);
    expect(fetching).toMatch(/about 33s left/i);
    expect(fetching).not.toMatch(/\(12s\)/);
    const packed = studioWorkingMessage({
      elapsedSec: 45,
      hasPack: true,
      packCitation: 'cite:youtube:auJzb1D-fag · v0',
      hasTranscript: false,
    });
    expect(packed).toMatch(/2\/3 transcript/i);
    expect(packed).toMatch(/pack ready/i);
    expect(packed).toContain('auJzb1D-fag');
    expect(packed).not.toContain('pBsT6v-ciO8');
    expect(packed).toMatch(/taking longer|retry/i);
    expect(packed).not.toMatch(/\(45s\)/);
    expect(packed).not.toBe('Fetching transcript…');
    expect(
      studioWorkingMessage({
        elapsedSec: 8,
        hasPack: true,
        hasTranscript: true,
      }),
    ).toMatch(/3\/3 analysis/i);
  });

  it('offers retry after the typical transcript wait or a failed run', () => {
    expect(
      studioShowTranscriptRetry({
        busy: true,
        elapsedSec: 44,
        hasTranscript: false,
        runStatus: 'processing',
      }),
    ).toBe(false);
    expect(
      studioShowTranscriptRetry({
        busy: true,
        elapsedSec: 45,
        hasTranscript: false,
        runStatus: 'processing',
      }),
    ).toBe(true);
    expect(
      studioShowTranscriptRetry({
        busy: false,
        elapsedSec: 10,
        hasTranscript: false,
        runStatus: 'failed',
      }),
    ).toBe(true);
    expect(
      studioShowTranscriptRetry({
        busy: false,
        elapsedSec: 45,
        hasTranscript: true,
        runStatus: 'complete',
      }),
    ).toBe(false);
  });

  it('labels review_action as a proposed finding, not an executed tool', () => {
    expect(
      studioActActionLabel({
        tool: 'review_action',
        status: 'proposed',
        result: 'Draft the SeaDance ad loop',
      }),
    ).toEqual({
      title: 'Draft the SeaDance ad loop',
      detail: 'Proposed from this run — not an executed tool.',
    });
  });

  it('describes tools-only export without claiming architecture', () => {
    expect(
      studioExportOutcomeMessage({
        toolCount: 2,
        hasArchitecture: false,
        artifactCount: 0,
      }),
    ).toMatch(/named tools/i);
    expect(
      studioExportOutcomeMessage({
        toolCount: 2,
        hasArchitecture: false,
        artifactCount: 0,
      }),
    ).not.toMatch(/architecture|artifacts/i);
    expect(
      studioExportOutcomeMessage({
        hasLinkedSop: true,
        toolCount: 0,
      }),
    ).toMatch(/SOP/);
    expect(
      studioExportOutcomeMessage({
        hasLinkedSop: true,
        toolCount: 0,
      }),
    ).not.toMatch(/named tools/i);
  });

  it('enables export from pack formation when events[] is empty', () => {
    expect(
      studioCanExport({
        transcript: 'x'.repeat(50),
        eventCount: 0,
        hasArchitecture: true,
        artifactCount: 2,
        toolCount: 1,
      }),
    ).toBe(true);
    expect(
      studioCanExport({
        transcript: '',
        eventCount: 0,
        hasArchitecture: false,
        artifactCount: 0,
        toolCount: 0,
      }),
    ).toBe(false);
  });

  it('names an invalid ?video= handoff instead of staying silent', () => {
    expect(studioInvalidHandoffMessage('https://www.youtube.com/watch')).toMatch(/valid youtube/i);
  });

  it('does not map keyframes or concepts into Studio events', () => {
    const studio = readFileSync(join(process.cwd(), 'src/components/OneLoopStudio.tsx'), 'utf8');
    expect(studio).toContain('studioEventsEmptyMessage');
    expect(studio).toContain('studioQueryFromSearchParams');
    expect(studio).toContain('studioCanExport');
    expect(studio).toContain('data-testid="studio-events-empty"');
    expect(studio).toContain('data-testid="pack-workbench"');
    expect(studio).toContain('data-testid="pack-workbench-tools"');
    expect(studio).toContain('data-testid="studio-working-state"');
    expect(studio).toContain('studioWorkingMessage');
    expect(studio).toContain('studioShowTranscriptRetry');
    expect(studio).toContain('data-testid="studio-transcript-retry"');
    expect(studio).toContain('Act on this run');
    expect(studio).toContain('stackCheckStatus');
    expect(studio).toContain('stackCheckStatusLabel');
    expect(studio).not.toMatch(/keyframes/);
    expect(studio).not.toMatch(/code_snippets/);
    expect(studio).not.toMatch(/mapKeyframes|fakeEvents|invent.*events/i);
  });
});