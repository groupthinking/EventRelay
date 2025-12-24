import { getObservability } from './observability';

/**
 * Helper for instrumenting Workflow.dev workflows with OpenTelemetry
 */
export class WorkflowInstrumentation {
  private obs = getObservability();

  /**
   * Trace a workflow execution
   */
  async traceWorkflow<T>(
    workflowName: string,
    workflowId: string,
    fn: () => Promise<T>
  ): Promise<T> {
    const startTime = Date.now();

    try {
      const result = await this.obs.trace(
        `workflow.${workflowName}`,
        {
          'workflow.name': workflowName,
          'workflow.id': workflowId,
          'workflow.status': 'running'
        },
        fn
      );

      // Record success metrics
      const duration = Date.now() - startTime;
      this.obs.recordDuration(`workflow.${workflowName}`, duration, {
        status: 'success',
        workflow_id: workflowId
      });

      this.obs.recordMetrics('workflow_executions_total', 1, {
        workflow: workflowName,
        status: 'success'
      });

      return result;
    } catch (error) {
      // Record failure metrics
      const duration = Date.now() - startTime;
      this.obs.recordDuration(`workflow.${workflowName}`, duration, {
        status: 'failure',
        workflow_id: workflowId
      });

      this.obs.recordMetrics('workflow_executions_total', 1, {
        workflow: workflowName,
        status: 'failure'
      });

      throw error;
    }
  }

  /**
   * Trace a workflow step
   */
  async traceStep<T>(
    workflowName: string,
    stepName: string,
    stepData: Record<string, any>,
    fn: () => Promise<T>
  ): Promise<T> {
    return await this.obs.trace(
      `workflow.${workflowName}.step.${stepName}`,
      {
        'workflow.name': workflowName,
        'step.name': stepName,
        ...stepData
      },
      fn
    );
  }
}

/**
 * Singleton instance
 */
let instrumentationInstance: WorkflowInstrumentation | null = null;

export function getWorkflowInstrumentation(): WorkflowInstrumentation {
  if (!instrumentationInstance) {
    instrumentationInstance = new WorkflowInstrumentation();
  }
  return instrumentationInstance;
}
