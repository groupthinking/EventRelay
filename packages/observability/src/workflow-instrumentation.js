"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.WorkflowInstrumentation = void 0;
exports.getWorkflowInstrumentation = getWorkflowInstrumentation;
const observability_1 = require("./observability");
/**
 * Helper for instrumenting Workflow.dev workflows with OpenTelemetry
 */
class WorkflowInstrumentation {
    obs = (0, observability_1.getObservability)();
    /**
     * Trace a workflow execution
     */
    async traceWorkflow(workflowName, workflowId, fn) {
        const startTime = Date.now();
        try {
            const result = await this.obs.trace(`workflow.${workflowName}`, {
                'workflow.name': workflowName,
                'workflow.id': workflowId,
                'workflow.status': 'running'
            }, fn);
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
        }
        catch (error) {
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
    async traceStep(workflowName, stepName, stepData, fn) {
        return await this.obs.trace(`workflow.${workflowName}.step.${stepName}`, {
            'workflow.name': workflowName,
            'step.name': stepName,
            ...stepData
        }, fn);
    }
}
exports.WorkflowInstrumentation = WorkflowInstrumentation;
/**
 * Singleton instance
 */
let instrumentationInstance = null;
function getWorkflowInstrumentation() {
    if (!instrumentationInstance) {
        instrumentationInstance = new WorkflowInstrumentation();
    }
    return instrumentationInstance;
}
//# sourceMappingURL=workflow-instrumentation.js.map