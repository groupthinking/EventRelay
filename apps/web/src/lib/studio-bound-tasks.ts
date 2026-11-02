import type { GroundedBuildSpec, ReviewInspection, SpecIssue } from './grounded-build-spec';

export interface StudioBoundTaskCheck {
  id: string;
  requirementId: string;
  given: string;
  when: string;
  then: string;
  status: 'not_run';
}

export type StudioBoundTaskCitation =
  GroundedBuildSpec['requirements'][number]['citations'][number] & {
    sourceUrl: string;
  };

export interface StudioBoundTask {
  id: string;
  title: string;
  detail: string;
  classification: GroundedBuildSpec['requirements'][number]['classification'];
  required: boolean;
  citations: StudioBoundTaskCitation[];
  checks: StudioBoundTaskCheck[];
  issues: SpecIssue[];
  executionStatus: 'not_run';
  outputStatus: 'not_generated';
  verificationStatus: 'unverified';
}

export type StudioBoundTasksView =
  | {
      status: 'unavailable' | 'invalid' | 'source-unavailable';
      tasks: [];
      issues: SpecIssue[];
    }
  | {
      status: 'available';
      source: GroundedBuildSpec['source'];
      contentHash: string;
      tasks: StudioBoundTask[];
      issues: SpecIssue[];
    };

/**
 * Project inspectGroundedSpec(pack)'s validated result into one task per
 * requirement. No title/position matching: checks bind by requirementId and
 * citations stay on their original requirement. This is a read-only view of a
 * proposed specification, never an execution or independent-check receipt.
 */
export function projectStudioBoundTasks(inspection: ReviewInspection): StudioBoundTasksView {
  if (inspection.status !== 'available') {
    return {
      status: inspection.status,
      tasks: [],
      issues: inspection.issues.map((item) => ({ ...item })),
    };
  }

  const { spec } = inspection;
  const checksByRequirement = new Map<string, StudioBoundTaskCheck[]>();
  for (const criterion of spec.acceptanceCriteria) {
    const checks = checksByRequirement.get(criterion.requirementId) ?? [];
    checks.push({ ...criterion, status: 'not_run' });
    checksByRequirement.set(criterion.requirementId, checks);
  }
  const issuePathsByRequirement = new Map<string, Set<string>>();
  for (const requirement of spec.requirements) {
    issuePathsByRequirement.set(requirement.id, new Set([requirement.id]));
  }
  for (const limitation of [...spec.unresolved, ...spec.unsupported]) {
    for (const requirementId of limitation.requirementIds) {
      issuePathsByRequirement.get(requirementId)?.add(limitation.id);
    }
  }

  return {
    status: 'available',
    source: { ...spec.source },
    contentHash: inspection.contentHash,
    issues: inspection.issues.map((item) => ({ ...item })),
    tasks: spec.requirements.map((requirement) => ({
      id: requirement.id,
      title: requirement.title,
      detail: requirement.detail,
      classification: requirement.classification,
      required: requirement.required,
      citations: requirement.citations.map((citation) => ({
        ...citation,
        sourceUrl: `https://www.youtube.com/watch?v=${encodeURIComponent(citation.videoId)}&t=${Math.floor(citation.startSeconds)}s`,
      })),
      checks: checksByRequirement.get(requirement.id) ?? [],
      issues: inspection.issues
        .filter((item) => !item.path || issuePathsByRequirement.get(requirement.id)?.has(item.path))
        .map((item) => ({ ...item })),
      executionStatus: 'not_run',
      outputStatus: 'not_generated',
      verificationStatus: 'unverified',
    })),
  };
}
