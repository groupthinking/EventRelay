/**
 * Helper for instrumenting Workflow.dev workflows with OpenTelemetry
 */
export declare class WorkflowInstrumentation {
    private obs;
    /**
     * Trace a workflow execution
     */
    traceWorkflow<T>(workflowName: string, workflowId: string, fn: () => Promise<T>): Promise<T>;
    /**
     * Trace a workflow step
     */
    traceStep<T>(workflowName: string, stepName: string, stepData: Record<string, any>, fn: () => Promise<T>): Promise<T>;
}
export declare function getWorkflowInstrumentation(): WorkflowInstrumentation;
