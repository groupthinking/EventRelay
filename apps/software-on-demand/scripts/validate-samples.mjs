import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  validateStepGraph,
  validateTraceEvents,
  loadGoldSetEvaluationFromFile,
} from "../src/validators.mjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");
const samplesDir = path.join(projectRoot, "samples");

function loadSampleJson(fileName) {
  const filePath = path.join(samplesDir, fileName);
  return JSON.parse(readFileSync(filePath, "utf8"));
}

function main() {
  try {
    const stepGraph = loadSampleJson("step_graph.sample.json");
    validateStepGraph(stepGraph);
    console.log("✓ step_graph.sample.json passed validation");

    const traceEvents = loadSampleJson("trace_events.sample.json");
    validateTraceEvents(traceEvents);
    console.log("✓ trace_events.sample.json passed validation");

    loadGoldSetEvaluationFromFile(
      path.join(samplesDir, "gold_set_sample.yaml")
    );
    console.log("✓ gold_set_sample.yaml passed validation");
  } catch (error) {
    console.error("Validation failed:", error.message);
    if (error.errors) {
      console.error("Details:", error.errors);
    }
    if (error.cause) {
      console.error("Cause:", error.cause.message);
      if (error.cause.errors) {
        console.error("Cause details:", error.cause.errors);
      }
    }
    process.exitCode = 1;
  }
}

main();
