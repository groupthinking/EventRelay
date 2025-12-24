/**
 * OpenTelemetry Observability Package
 * @packageDocumentation
 */

export {
  Observability,
  initObservability,
  getObservability
} from './observability';

export type { ObservabilityConfig } from './observability';

export {
  WorkflowInstrumentation,
  getWorkflowInstrumentation
} from './workflow-instrumentation';
