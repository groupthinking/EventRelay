'use client';

import type { EmittedVideoPack } from '@/lib/emit-video-pack';
import type { ProjectRecord } from '@/lib/projects/project-types';
import { buildProjectFolders } from '@/lib/projects/project-workspace';
import type { PackStatus } from './ProjectBriefView';

type ViewProps = { project: ProjectRecord; pack: EmittedVideoPack | null; packStatus: PackStatus };

/** Read-only preview of real extracted items. A full Elements library (filters, export) is planned. */
export function ProjectElementsView({ pack }: ViewProps) {
  const tools = (pack?.stack?.tools ?? []).filter((tool) => tool.name?.trim());
  const actions = pack?.action_items ?? [];
  const requirements = pack?.requirements ?? [];
  const keyframes = pack?.keyframes ?? [];
  const empty = tools.length + actions.length + requirements.length + keyframes.length === 0;

  return (
    <div className="pw-main" data-testid="project-elements">
      <p className="pw-banner">
        A read-only preview of what was extracted from this video. A full Elements library with
        filters and export is planned.
      </p>
      {empty ? (
        <p className="pw-card pw-muted">No elements were extracted yet. Extract the Video Pack first.</p>
      ) : (
        <div className="pw-grid-2">
          <section className="pw-card" aria-labelledby="el-tools">
            <h2 id="el-tools">Tools ({tools.length})</h2>
            {tools.length === 0 ? (
              <p className="pw-muted">None detected.</p>
            ) : (
              <ul className="pw-list">
                {tools.map((tool) => (
                  <li key={tool.name}>
                    {tool.name}
                    {tool.kind ? <span className="pw-muted"> · {tool.kind}</span> : null}
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section className="pw-card" aria-labelledby="el-actions">
            <h2 id="el-actions">Tasks ({actions.length + requirements.length})</h2>
            {actions.length + requirements.length === 0 ? (
              <p className="pw-muted">None extracted.</p>
            ) : (
              <ul className="pw-list">
                {actions.map((item) => (
                  <li key={`a-${item.id}`}>{item.title}</li>
                ))}
                {requirements.map((item) => (
                  <li key={`r-${item.id}`}>{item.title}</li>
                ))}
              </ul>
            )}
          </section>
          <section className="pw-card" aria-labelledby="el-frames">
            <h2 id="el-frames">Keyframes ({keyframes.length})</h2>
            <p className="pw-muted">
              {keyframes.length === 0 ? 'None captured.' : `${keyframes.length} keyframe(s) captured from the video.`}
            </p>
          </section>
        </div>
      )}
    </div>
  );
}

/** Read-only linear summary of the pipeline. An interactive node graph is planned. */
export function ProjectCanvasView({ project, pack, packStatus }: ViewProps) {
  const folders = buildProjectFolders(pack);
  const chapters = folders.length - 1;
  const tasks = folders[0].taskCount ?? 0;
  const checks = (pack?.stack?.tools ?? []).filter((tool) => tool.check?.trim()).length;
  const stages: Array<{ name: string; value: string }> = [
    { name: 'Source', value: project.videoId },
    { name: 'Pack', value: pack ? 'Extracted' : packStatus === 'processing' ? 'Extracting' : 'Not extracted' },
    { name: 'Chapters', value: String(chapters) },
    { name: 'Tasks', value: String(tasks) },
    { name: 'Checks', value: `${checks} proposed` },
  ];
  return (
    <div className="pw-main" data-testid="project-canvas">
      <p className="pw-banner">
        A read-only summary of this project&apos;s pipeline. Checks are proposed, not run. An interactive
        canvas is planned.
      </p>
      <ol className="pw-stages" aria-label="Pipeline stages">
        {stages.map((stage) => (
          <li key={stage.name} className="pw-stage">
            <span className="pw-stage-name">{stage.name}</span>
            <span className="pw-stage-value">{stage.value}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
