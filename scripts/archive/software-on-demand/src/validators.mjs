import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { parse as parseYaml } from "yaml";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");

const ajv = new Ajv2020({
  allErrors: true,
  strict: false,
});
addFormats(ajv);

// Load and compile JSON schemas once.
const stepGraphSchema = JSON.parse(
  readFileSync(path.join(projectRoot, "step_graph.schema.json"), "utf8")
);
const traceEventSchema = JSON.parse(
  readFileSync(path.join(projectRoot, "trace_ui_event_schema.json"), "utf8")
);

const stepGraphValidator = ajv.compile(stepGraphSchema);
const traceEventValidator = ajv.compile(traceEventSchema);

function formatValidationError(errors = []) {
  return errors
    .map((err) => {
      const dataPath = err.instancePath || err.dataPath || "(root)";
      return `${dataPath} ${err.message ?? ""}`.trim();
    })
    .join("; ");
}

export function validateStepGraph(graph) {
  if (!stepGraphValidator(graph)) {
    const error = new Error(
      `Invalid step graph payload: ${formatValidationError(
        stepGraphValidator.errors
      )}`
    );
    error.errors = stepGraphValidator.errors;
    throw error;
  }

  return graph;
}

export function validateTraceEvent(event) {
  if (!traceEventValidator(event)) {
    const error = new Error(
      `Invalid trace event payload: ${formatValidationError(
        traceEventValidator.errors
      )}`
    );
    error.errors = traceEventValidator.errors;
    throw error;
  }

  return event;
}

export function validateTraceEvents(events) {
  if (!Array.isArray(events)) {
    throw new Error("Trace events payload must be an array.");
  }

  return events.map((event, index) => {
    try {
      return validateTraceEvent(event);
    } catch (error) {
      const wrapped = new Error(`Trace event ${index} failed validation`);
      wrapped.cause = error;
      throw wrapped;
    }
  });
}

export function parseGoldSetEvaluation(yamlSource) {
  const doc = parseYaml(yamlSource);
  if (typeof doc !== "object" || doc === null) {
    throw new Error("Gold-set evaluation YAML must parse to an object.");
  }
  return doc;
}

export function validateGoldSetEvaluation(doc) {
  if (typeof doc !== "object" || doc === null) {
    throw new Error("Gold-set evaluation must be an object.");
  }

  const requiredTopLevel = [
    "metadata",
    "execution_context",
    "expected_outcomes",
    "run_observation",
    "metric_scores",
    "annotations",
    "verdict",
  ];

  for (const key of requiredTopLevel) {
    if (!(key in doc)) {
      throw new Error(`Gold-set evaluation missing required key '${key}'.`);
    }
  }

  if (!Array.isArray(doc.expected_outcomes?.deliverables)) {
    throw new Error(
      "Gold-set evaluation expected_outcomes.deliverables must be an array."
    );
  }

  if (!Array.isArray(doc.expected_outcomes?.commands)) {
    throw new Error(
      "Gold-set evaluation expected_outcomes.commands must be an array."
    );
  }

  return doc;
}

export function loadGoldSetEvaluationFromFile(filePath) {
  const yamlSource = readFileSync(filePath, "utf8");
  const doc = parseGoldSetEvaluation(yamlSource);
  return validateGoldSetEvaluation(doc);
}

export default {
  validateStepGraph,
  validateTraceEvent,
  validateTraceEvents,
  loadGoldSetEvaluationFromFile,
  validateGoldSetEvaluation,
  parseGoldSetEvaluation,
};
