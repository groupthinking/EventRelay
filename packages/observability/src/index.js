"use strict";
/**
 * OpenTelemetry Observability Package
 * @packageDocumentation
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.getWorkflowInstrumentation = exports.WorkflowInstrumentation = exports.getObservability = exports.initObservability = exports.Observability = void 0;
var observability_1 = require("./observability");
Object.defineProperty(exports, "Observability", { enumerable: true, get: function () { return observability_1.Observability; } });
Object.defineProperty(exports, "initObservability", { enumerable: true, get: function () { return observability_1.initObservability; } });
Object.defineProperty(exports, "getObservability", { enumerable: true, get: function () { return observability_1.getObservability; } });
var workflow_instrumentation_1 = require("./workflow-instrumentation");
Object.defineProperty(exports, "WorkflowInstrumentation", { enumerable: true, get: function () { return workflow_instrumentation_1.WorkflowInstrumentation; } });
Object.defineProperty(exports, "getWorkflowInstrumentation", { enumerable: true, get: function () { return workflow_instrumentation_1.getWorkflowInstrumentation; } });
//# sourceMappingURL=index.js.map