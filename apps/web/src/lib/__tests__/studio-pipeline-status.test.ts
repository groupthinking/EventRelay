import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import {
  STUDIO_PRODUCT_TAGLINE,
  studioActionCard,
  studioCanExport,
  studioCanRetryTranscript,
  studioDeployButtonLabel,
  studioDeployEnabledHint,
  studioDeployOutcomeMessage,
  studioDeployReceiptForSelection,
  studioEventsEmptyMessage,
  studioExportFilename,
  studioExportToastMessage,
  studioHasDeployReceipt,
  studioVerifiedLiveUrl,
  studioInvalidHandoffMessage,
  studioPackCitation,
  studioPackIdentity,
  studioResolveAutoSelectedPackId,
  studioFormationSupplementalEntities,
  studioPackFormation,
  studioPasteOutcomeMessage,
  studioPlayerOverlay,
  studioPlayerPhase,
  studioPromotePackWorkbench,
  studioRunQuality,
  studioStatusLabel,
  studioStatusMessage,
  studioJobStripDestination,
  studioTranscriptBody,
  studioTranscriptEtaLabel,
  studioTranscriptStage,
  studioWorkbenchEmptyView,
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
    expect(studio).toContain('packFormation.checks');
    expect(studio).not.toMatch(/router\.(push|replace)\(['"]\/dashboard/);
  });

  it('suppresses transcript-only tool chips when pack.stack.tools are grounded', () => {
    expect(
      studioFormationSupplementalEntities(
        [{ name: 'Cloudflare' }, { name: 'x402' }],
        [
          {
            name: 'Shopify',
            kind: 'platform',
            officialUrl: 'https://shopify.dev',
            docsUrl: 'https://shopify.dev/docs',
            timestamps: [],
          },
        ],
      ),
    ).toEqual([]);

    expect(
      studioFormationSupplementalEntities([], [
        {
          name: 'Shopify',
          kind: 'platform',
          officialUrl: 'https://shopify.dev',
          docsUrl: 'https://shopify.dev/docs',
          timestamps: [],
        },
      ]).map((entity) => entity.name),
    ).toEqual(['Shopify']);
  });

  it('tells the truth when events[] is empty after a completed run', () => {
    expect(
      studioEventsEmptyMessage({
        busy: true,
        hasCompletedRun: false,
        eventCount: 0,
        hasArchitecture: true,
        artifactCount: 2,
        toolCount: 1,
      }),
    ).toMatch(/extracting events/i);
    expect(
      studioEventsEmptyMessage({
        busy: false,
        hasCompletedRun: false,
        eventCount: 0,
        hasArchitecture: false,
        artifactCount: 0,
        toolCount: 0,
      }),
    ).toBe('Events show up after Run.');

    const emptyWithPack = studioEventsEmptyMessage({
      busy: false,
      hasCompletedRun: true,
      eventCount: 0,
      hasArchitecture: true,
      artifactCount: 2,
      toolCount: 1,
    });
    expect(emptyWithPack.toLowerCase()).not.toContain('show up after run');
    expect(emptyWithPack.toLowerCase()).not.toContain('extracting');
    expect(emptyWithPack.toLowerCase()).toMatch(/no extracted events/);
    expect(emptyWithPack.toLowerCase()).toMatch(/architecture|artifacts|stack/);
    expect(studioPromotePackWorkbench({ eventCount: 0, hasArchitecture: true, artifactCount: 2, toolCount: 1 })).toBe(
      true,
    );
    expect(studioPromotePackWorkbench({ eventCount: 3, hasArchitecture: true, artifactCount: 2, toolCount: 1 })).toBe(
      false,
    );
  });

  it('does not claim a transcript exists when a completed run only has pack identity', () => {
    const emptyNoTranscript = studioEventsEmptyMessage({
      busy: false,
      hasCompletedRun: true,
      eventCount: 0,
      hasArchitecture: false,
      artifactCount: 0,
      toolCount: 0,
      hasTranscript: false,
    });

    expect(emptyNoTranscript.toLowerCase()).toMatch(/no extracted events/);
    expect(emptyNoTranscript.toLowerCase()).not.toContain('transcript');
    expect(emptyNoTranscript.toLowerCase()).toContain('pack identity');
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

    const dashboardPanels = readFileSync(
      join(process.cwd(), 'src/components/dashboard/panels.tsx'),
      'utf8',
    );
    expect(dashboardPanels).toContain('actionsFromStudioRun');
    expect(dashboardPanels).toContain('studioCanExport');
  });

  it('names an invalid ?video= handoff instead of staying silent', () => {
    expect(studioInvalidHandoffMessage('https://www.youtube.com/watch')).toMatch(/valid youtube/i);
  });

  it('names transcript stages, ETA, and when retry is available', () => {
    expect(studioTranscriptStage({ busy: true, elapsedSeconds: 2 }).id).toBe('pack');
    expect(studioTranscriptStage({ busy: true, elapsedSeconds: 2 }).label).toMatch(/pack identity/i);
    expect(
      studioTranscriptStage({ busy: true, elapsedSeconds: 12, hasPack: true, progress: 8 }).id,
    ).toBe('captions');
    expect(
      studioTranscriptStage({
        busy: true,
        elapsedSeconds: 20,
        hasPack: true,
        progress: 12,
      }).id,
    ).toBe('transcript');
    expect(
      studioTranscriptStage({
        busy: true,
        elapsedSeconds: 30,
        hasTranscript: true,
      }).id,
    ).toBe('events');
    expect(studioTranscriptStage({ busy: false, elapsedSeconds: 40, hasTranscript: true }).id).toBe(
      'ready',
    );
    expect(studioTranscriptStage({ busy: false, elapsedSeconds: 12, hasFailed: true }).id).toBe(
      'failed',
    );
    // Pack identity short-circuits the open-ended "Building transcript" label
    // even when the elapsed/progress heuristics would otherwise report it.
    const identityStage = studioTranscriptStage({
      busy: true,
      elapsedSeconds: 40,
      progress: 12,
      hasPackIdentity: true,
    });
    expect(identityStage.id).toBe('pack');
    expect(identityStage.label).toMatch(/pack identity/i);
    expect(identityStage.label).not.toMatch(/building transcript/i);
    // A real transcript still advances past pack identity to events.
    expect(
      studioTranscriptStage({
        busy: true,
        elapsedSeconds: 40,
        hasPackIdentity: true,
        hasTranscript: true,
      }).id,
    ).toBe('events');
    expect(
      studioTranscriptBody({ transcript: '', busy: false, failed: false }),
    ).toBe('Nothing yet.');
    expect(
      studioTranscriptBody({
        transcript: '   ',
        busy: false,
        failed: true,
        failureMessage: 'Gemini 3.8 Flash returned no extracted spec content.',
      }),
    ).toBe('Gemini 3.8 Flash returned no extracted spec content.');
    expect(
      studioTranscriptBody({ transcript: null, busy: false, failed: true, failureMessage: '  ' }),
    ).toBe('Transcript failed.');
    expect(studioJobStripDestination(null)).toEqual({
      kind: 'studio',
      label: '/studio',
      href: '/studio',
    });
    expect(studioJobStripDestination('auJzb1D-fag')).toEqual({
      kind: 'video',
      label: 'auJzb1D-fag',
    });
    expect(JSON.stringify(studioJobStripDestination('auJzb1D-fag'))).not.toContain('/d/');
    expect(studioTranscriptEtaLabel(10)).toMatch(/about 35s left/i);
    expect(studioTranscriptEtaLabel(45)).toMatch(/typical/i);
    expect(studioCanRetryTranscript({ busy: false, hasFailed: true, retryable: true })).toBe(true);
    expect(studioCanRetryTranscript({ busy: true, elapsedSeconds: 20 })).toBe(false);
    expect(studioCanRetryTranscript({ busy: true, elapsedSeconds: 90 })).toBe(true);

    const studio = readFileSync(join(process.cwd(), 'src/components/OneLoopStudio.tsx'), 'utf8');
    expect(studio).toContain('studioTranscriptStage');
    expect(studio).toContain('studioTranscriptEtaLabel');
    expect(studio).toContain('data-testid="studio-transcript-stage"');
    expect(studio).toContain('data-testid="studio-transcript-retry"');
  });

  it('does not claim Deploy completed without a verified live receipt', () => {
    expect(
      studioDeployOutcomeMessage({
        runStatus: 'failed',
        error: 'Deploy job job_1 still complete',
      }),
    ).toBe('Deploy job job_1 still complete');
    expect(
      studioDeployOutcomeMessage({
        runStatus: 'completed',
        kind: 'job',
        message: 'Backend job finished with no verified live URL',
      }),
    ).toBe('Backend job finished with no verified live URL');
    expect(
      studioDeployOutcomeMessage({
        runStatus: 'completed',
        kind: 'job',
        message: 'Backend job finished with no verified live URL',
      }),
    ).not.toMatch(/Deploy completed/i);
    const completedNoUrl = studioDeployOutcomeMessage({ runStatus: 'completed' });
    expect(completedNoUrl.toLowerCase()).not.toMatch(/deploy completed/);
    expect(completedNoUrl.toLowerCase()).not.toMatch(/\bsuccess(?:ful|fully)?\b/);
    expect(completedNoUrl).toMatch(/no verified deploy receipt/i);
    expect(studioHasDeployReceipt(null)).toBe(false);
    expect(studioHasDeployReceipt('http://example.vercel.app')).toBe(false);
    expect(studioHasDeployReceipt('https://')).toBe(false);
    expect(studioHasDeployReceipt('https:///')).toBe(false);
    expect(studioVerifiedLiveUrl('https://')).toBeNull();
    expect(studioVerifiedLiveUrl('https://example.vercel.app')).toBe('https://example.vercel.app');

    const withReceipt = studioDeployOutcomeMessage({
      runStatus: 'completed',
      liveUrl: 'https://example.vercel.app',
    });
    expect(withReceipt).toContain('https://example.vercel.app');
    expect(withReceipt.toLowerCase()).not.toMatch(/deploy completed/);
    expect(studioHasDeployReceipt('https://example.vercel.app')).toBe(true);

    const abortHold = studioDeployOutcomeMessage({
      runStatus: 'failed',
      error: 'The operation was aborted due to timeout',
    });
    expect(abortHold).not.toMatch(/aborted due to timeout/i);
    expect(abortHold.toLowerCase()).not.toMatch(/deploy completed/);
    expect(abortHold).toMatch(/timed out|origin job|waiting/i);

    for (const runStatus of ['pending', 'running', 'queued'] as const) {
      const inFlight = studioDeployOutcomeMessage({
        runStatus,
        jobId: 'job_96f498640b',
        jobStatus: 'transcribing',
      });
      expect(inFlight.toLowerCase()).not.toMatch(/finished|completed|success/);
      expect(inFlight.toLowerCase()).not.toMatch(/deploy completed/);
      expect(inFlight).not.toMatch(/UNKNOWN checks are not a live URL/);
      expect(inFlight).toMatch(/job_96f498640b still transcribing/);
      expect(inFlight.toLowerCase()).toMatch(/still|pending|running|queued|transcribing/);
    }

    expect(
      studioDeployReceiptForSelection({
        selectedVideoId: 'pBsT6v-ciO8',
        receiptVideoId: 'other-id',
        liveUrl: 'https://example.vercel.app',
      }),
    ).toBeNull();
    expect(
      studioDeployReceiptForSelection({
        selectedVideoId: 'pBsT6v-ciO8',
        receiptVideoId: 'pBsT6v-ciO8',
        liveUrl: 'https://example.vercel.app',
      }),
    ).toBe('https://example.vercel.app');
    expect(
      studioDeployReceiptForSelection({
        selectedVideoId: 'pBsT6v-ciO8',
        receiptVideoId: 'pBsT6v-ciO8',
        liveUrl: 'https://',
      }),
    ).toBeNull();

    expect(studioDeployButtonLabel(false)).toBe('Check preflight');
    expect(studioDeployButtonLabel(true)).toBe('Check preflight');
    for (const hasReceipt of [false, true]) {
      expect(studioDeployEnabledHint(hasReceipt)).toMatch(/preflight only/i);
      expect(studioDeployEnabledHint(hasReceipt)).toMatch(/deployment is unavailable/i);
    }

    const studio = readFileSync(join(process.cwd(), 'src/components/OneLoopStudio.tsx'), 'utf8');
    expect(studio).toContain('studioDeployOutcomeMessage');
    expect(studio).not.toMatch(/pollStudioDeploy\([^)]*attempts:\s*20\b/);
    expect(studio).toContain('startStudioDeploy({ url: next })');
    expect(studio).toContain('usableProvidedTranscript');
    const workflow = readFileSync(join(process.cwd(), 'src/workflows/studio-deploy.ts'), 'utf8');
    expect(workflow).toMatch(/kickoffAsyncVideoJob\(url,\s*\{\s*transcript/);
    expect(workflow).toMatch(/isAbortTimeout|retryable/);
    expect(workflow).not.toMatch(/studioDeployReadyTranscriptHold\(\s*\)/);
    expect(workflow).toMatch(/STUDIO_ORIGIN_KICKOFF_NO_JOB_HOLD/);
    expect(workflow).not.toMatch(/transcript\s*\n\s*\? STUDIO_ORIGIN_NO_HOSTNAME_HOLD/);
    expect(workflow).toMatch(/KICKOFF_RETRIES|kickoffRetries|for \(let i = 0; i < .*KICKOFF/);
    const kickoffRetryMatch = workflow.match(/const KICKOFF_RETRIES\s*=\s*(\d+)/);
    expect(kickoffRetryMatch).not.toBeNull();
    expect(Number(kickoffRetryMatch?.[1])).toBeLessThanOrEqual(1);
    const retryLoop = workflow.slice(workflow.indexOf('KICKOFF_RETRIES'));
    const afterRetries = retryLoop.slice(0, retryLoop.indexOf('if (kicked.kind === \'live\''));
    expect(afterRetries).toMatch(/kind:\s*['"]handoff['"]/);
    expect(afterRetries).not.toMatch(/throw new FatalError\(kicked\.message/);
    expect(workflow).toMatch(/catch/);
    expect(workflow).toMatch(/import \{[^}]*sleep[^}]*\} from ['"]workflow['"]/);
    expect(workflow).toMatch(/await sleep\(['"]10s['"]\)/);
    expect(workflow).toMatch(/decideStudioDeployPoll/);
    expect(workflow).not.toMatch(/setTimeout/);
    expect(workflow).not.toMatch(/AbortSignal\.timeout/);
    const asyncJob = readFileSync(join(process.cwd(), 'src/lib/pipeline-async-job.ts'), 'utf8');
    expect(asyncJob).toMatch(/STUDIO_ORIGIN_KICKOFF_NO_JOB_HOLD/);
    expect(asyncJob).toMatch(/AbortSignal\.timeout\(45_000\)/);
    expect(asyncJob).not.toMatch(/isGatewayTimeoutKickoff\(undefined, message\) \{\s*return STUDIO_ORIGIN_NO_HOSTNAME_HOLD/);
    expect(studio).toContain('studioDeployButtonLabel');
    expect(studio).toContain('studioDeployReceiptForSelection');
    expect(studio).toContain('studioVerifiedLiveUrl');
    expect(studio).toContain('setDeployReceiptUrl(null)');
    expect(studio).toContain('setGateReceipt(null)');
    expect(studio).not.toContain('STUDIO_DEPLOY_ATTEMPT_STARTED_HOLD');
    expect(studio).not.toContain('Deploy attempt started. Waiting for a verified https live URL.');
    expect(studio).not.toContain('Deploy ${polled.runStatus');
    expect(studio).not.toMatch(/`Deploy \$\{polled\.runStatus/);
    expect(studio).not.toContain('>Deploy<');
  });

  it('softens reviewed/durable overclaim copy and pads the sticky footer', () => {
    expect(STUDIO_PRODUCT_TAGLINE.toLowerCase()).not.toMatch(/reviewed actions|durable workflows/);
    expect(STUDIO_PRODUCT_TAGLINE).toMatch(/video pack/i);

    const footer = readFileSync(join(process.cwd(), 'src/components/Footer.tsx'), 'utf8');
    const studio = readFileSync(join(process.cwd(), 'src/components/OneLoopStudio.tsx'), 'utf8');
    const retired = readFileSync(join(process.cwd(), 'src/components/VideoWorkflowStudio.tsx'), 'utf8');
    const pricing = readFileSync(join(process.cwd(), 'src/app/pricing/page.tsx'), 'utf8');
    const apiDocs = readFileSync(join(process.cwd(), 'src/app/docs/api/page.tsx'), 'utf8');
    expect(footer).toContain('STUDIO_PRODUCT_TAGLINE');
    expect(footer.toLowerCase()).not.toContain('reviewed actions');
    expect(footer.toLowerCase()).not.toContain('durable workflows');
    expect(studio).toContain('data-testid="studio-main"');
    expect(studio).toMatch(/pb-28|padding-bottom/);
    expect(pricing).not.toMatch(/reviewed plan dispatches backend agents/);
    expect(apiDocs).not.toMatch(/durable Studio analysis workflow/);
    expect(retired).not.toMatch(/Starting durable/);
    expect(retired).not.toMatch(/Could not start durable workflow/);
    expect(retired).not.toMatch(/runs a durable video-to-transcript/);
    expect(retired).not.toMatch(/signed-in durable workflow/);
    expect(retired).not.toMatch(/durable Workflow DevKit/);
  });

  it('does not claim live deploy in retired studio without a verified receipt guard', () => {
    const retired = readFileSync(join(process.cwd(), 'src/components/VideoWorkflowStudio.tsx'), 'utf8');
    expect(retired).toContain('studioVerifiedLiveUrl');
    expect(retired).not.toContain('setActionMessage(`Deploy live: ${kick.live_url}`)');
    expect(retired).not.toContain('setActionMessage(`Deploy ready: ${polled.live_url}`)');
  });

  it('renders review_action as a card with status, title, and detail', () => {
    const review = studioActionCard({
      tool: 'review_action',
      status: 'proposed',
      result: 'Review evidence',
    });
    expect(review.kind).toBe('review');
    expect(review.title).toMatch(/review this result/i);
    expect(review.statusLabel).toBe('Needs review');
    expect(review.detail).toBe('Review evidence');

    const tool = studioActionCard({ tool: 'persist_insight', status: 'completed' });
    expect(tool.kind).toBe('tool');
    expect(tool.title).toMatch(/persist insight/i);
    expect(tool.statusLabel).toBe('Done');
    expect(tool.detail).toMatch(/no detail/i);

    const studio = readFileSync(join(process.cwd(), 'src/components/OneLoopStudio.tsx'), 'utf8');
    expect(studio).toContain('studioActionCard');
    expect(studio).toContain('data-testid="studio-action-card"');
  });

  it('returns a toast for export success and failure including filename', () => {
    expect(studioExportFilename('AI Gold Rushes')).toBe('AI Gold Rushes.zip');
    const filename = 'AI Gold Rushes.zip';
    const pack = studioExportToastMessage({
      ok: true,
      kind: 'pack',
      filename,
    });
    expect(pack.tone).toBe('success');
    expect(pack.text).toMatch(/pack exported/i);
    expect(pack.text).toContain(filename);
    expect(studioExportToastMessage({ ok: true, kind: 'sop' }).tone).toBe('success');
    const failed = studioExportToastMessage({ ok: false, error: 'Disk full', filename });
    expect(failed.tone).toBe('error');
    expect(failed.text).toContain('Disk full');
    expect(failed.text).toContain(filename);
    expect(studioExportToastMessage({ ok: false, kind: 'empty' }).tone).toBe('error');

    const studio = readFileSync(join(process.cwd(), 'src/components/OneLoopStudio.tsx'), 'utf8');
    expect(studio).toContain('studioExportToastMessage');
    expect(studio).toContain('studioExportFilename');
    expect(studio).toContain('data-testid="studio-export-toast"');
    expect(studio).not.toMatch(/setExportToast\(toast\);\s*setMessage\(/);
    expect(studio).toMatch(/role=\{exportToast\.tone === 'error' \? 'alert' : 'status'\}/);
  });

  it('covers the player until load and names a load error instead of silent 0:00', () => {
    expect(studioPlayerPhase({ videoId: null })).toBe('empty');
    expect(studioPlayerPhase({ videoId: 'pBsT6v-ciO8' })).toBe('loading');
    expect(studioPlayerPhase({ videoId: 'pBsT6v-ciO8', loaded: true })).toBe('ready');
    expect(studioPlayerPhase({ videoId: 'pBsT6v-ciO8', failed: true })).toBe('error');
    expect(studioPlayerPhase({ videoId: 'pBsT6v-ciO8', timedOut: true })).toBe('error');
    expect(studioPlayerOverlay('loading')).toMatch(/loading video/i);
    expect(studioPlayerOverlay('error')).toMatch(/did not load/i);
    expect(studioPlayerOverlay('ready')).toBeNull();
    expect(studioPlayerOverlay('empty')).toBeNull();

    const studio = readFileSync(join(process.cwd(), 'src/components/OneLoopStudio.tsx'), 'utf8');
    expect(studio).toContain('studioPlayerPhase');
    expect(studio).toContain('data-testid="studio-player-overlay"');
    expect(studio).toContain('data-testid="studio-player-retry"');
    expect(studio).toContain('useYouTubePlayer');
    expect(studio).toMatch(/seekTo\(/);
    expect(studio).not.toMatch(/onLoad=\{\(\) => setPlayerLoaded/);
    expect(studio).not.toMatch(/0:00/);
  });

  it('describes workbench empty states when no pack is stored', () => {
    expect(
      studioWorkbenchEmptyView({
        busy: false,
        hasSelection: false,
        hasVideoPack: false,
        analysisReady: false,
      })?.title,
    ).toMatch(/no video/i);
    expect(
      studioWorkbenchEmptyView({
        busy: true,
        hasSelection: true,
        hasVideoPack: false,
        analysisReady: false,
      })?.title,
    ).toMatch(/in progress/i);
    expect(
      studioWorkbenchEmptyView({
        busy: false,
        hasSelection: true,
        hasVideoPack: true,
        analysisReady: true,
      }),
    ).toBeNull();

    const studio = readFileSync(join(process.cwd(), 'src/components/OneLoopStudio.tsx'), 'utf8');
    expect(studio).toContain('data-testid="studio-workbench-empty"');
    expect(studio).toContain('studioWorkbenchEmptyView');
    expect(studio).toContain('data-testid="studio-build-live-failure"');
    expect(studio).not.toContain('/d/{videoId}');
    expect(studio).not.toContain("{'{videoId}'}");
    expect(studio).toContain('studioJobStripDestination');
    expect(studio).toContain('studioTranscriptBody');
    expect(
      studioWorkbenchEmptyView({
        busy: false,
        hasSelection: true,
        hasVideoPack: false,
        analysisReady: false,
        failed: true,
        failureMessage: 'Gemini 3.8 Flash returned no extracted spec content.',
      })?.description,
    ).toBe('Gemini 3.8 Flash returned no extracted spec content.');
  });

  it('does not map keyframes or concepts into Studio events', () => {
    const studio = readFileSync(join(process.cwd(), 'src/components/OneLoopStudio.tsx'), 'utf8');
    expect(studio).toContain('studioEventsEmptyMessage');
    expect(studio).toContain('studioQueryFromSearchParams');
    expect(studio).toContain('studioCanExport');
    expect(studio).toContain('data-testid="studio-events-empty"');
    expect(studio).toContain('data-testid="pack-workbench"');
    expect(studio).not.toMatch(/keyframes/);
    expect(studio).not.toMatch(/code_snippets/);
    expect(studio).not.toMatch(/mapKeyframes|fakeEvents|invent.*events/i);
  });

  it('selects a stored pack for the header without a Stored packs combobox click (#2244)', () => {
    const studio = readFileSync(join(process.cwd(), 'src/components/OneLoopStudio.tsx'), 'utf8');
    // The header/transcript follow a resolved selection, and pack identity is
    // wired into the transcript stage so the status leaves "Building transcript".
    expect(studio).toContain('studioResolveAutoSelectedPackId');
    expect(studio).toContain('studioPackIdentity');
    expect(studio).toContain('hasPackIdentity');
    // Combobox change still drives selection via the store.
    expect(studio).toMatch(/onChange=\{\(event\) => selectVideo\(event\.target\.value \|\| null\)\}/);
  });
});

function fixturePackCitation(overrides?: {
  videoId?: string;
  sourceUrl?: string | null;
  sourceHash?: string | null;
}) {
  const videoId = overrides?.videoId ?? 'auJzb1D-fag';
  const sourceUrl =
    overrides && 'sourceUrl' in overrides
      ? overrides.sourceUrl
      : `https://www.youtube.com/watch?v=${videoId}`;
  const sourceHash =
    overrides && 'sourceHash' in overrides
      ? overrides.sourceHash
      : '2778c5fc21eef3d12a4543ce2108ca28fd6f829db1da120d7e75655ab471f97d';
  return {
    version: 'v0',
    videoId,
    packId: `vp:v0:${videoId}`,
    sourceUrl: sourceUrl ?? '',
    sourceHash: sourceHash ?? '',
    pack: {
      version: 'v0',
      id: `vp:v0:${videoId}`,
      video_id: videoId,
      source_url: sourceUrl ?? '',
      provenance: { source_hash: sourceHash ?? '' },
    },
  };
}

describe('studioPackIdentity', () => {
  it('returns the youtube id and citation when source_url + source_hash exist', () => {
    const identity = studioPackIdentity(fixturePackCitation());
    expect(identity).not.toBeNull();
    expect(identity?.videoId).toBe('auJzb1D-fag');
    expect(identity?.citation).toContain('cite:youtube:auJzb1D-fag');
  });

  it('returns null when the pack is missing or lacks identity fields', () => {
    expect(studioPackIdentity(null)).toBeNull();
    expect(studioPackIdentity(undefined)).toBeNull();
    expect(studioPackIdentity(fixturePackCitation({ sourceUrl: '' }))).toBeNull();
    expect(studioPackIdentity(fixturePackCitation({ sourceHash: '   ' }))).toBeNull();
  });
});

describe('studioResolveAutoSelectedPackId', () => {
  it('picks the newest stored pack with identity when nothing is selected', () => {
    const target = studioResolveAutoSelectedPackId({
      selectedVideoId: null,
      videos: [
        { id: 'newest', videoPack: fixturePackCitation({ videoId: 'auJzb1D-fag' }) },
        { id: 'older', videoPack: fixturePackCitation({ videoId: 'jNQXAC9IVRw' }) },
      ],
    });
    expect(target).toBe('newest');
  });

  it('skips rows without pack identity', () => {
    const target = studioResolveAutoSelectedPackId({
      selectedVideoId: null,
      videos: [
        { id: 'no-pack', videoPack: null },
        { id: 'no-identity', videoPack: fixturePackCitation({ sourceHash: '' }) },
        { id: 'ready', videoPack: fixturePackCitation() },
      ],
    });
    expect(target).toBe('ready');
  });

  it('never overrides an existing selection or a pending handoff', () => {
    expect(
      studioResolveAutoSelectedPackId({
        selectedVideoId: 'already',
        videos: [{ id: 'ready', videoPack: fixturePackCitation() }],
      }),
    ).toBeNull();
    expect(
      studioResolveAutoSelectedPackId({
        selectedVideoId: null,
        hasPendingHandoff: true,
        videos: [{ id: 'ready', videoPack: fixturePackCitation() }],
      }),
    ).toBeNull();
  });

  it('returns null when no stored pack exists', () => {
    expect(
      studioResolveAutoSelectedPackId({ selectedVideoId: null, videos: [] }),
    ).toBeNull();
  });
});
