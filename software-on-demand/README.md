Software-On-Demand Schemas & Validation
=======================================

This directory hosts schema definitions and helper utilities for the Software-On-Demand multi-agent runtime.

Contents
--------
- `gold_set_evaluation_template.yaml` – canonical template for manual/agent QA reviews.
- `step_graph.schema.json` – JSON Schema describing the orchestrator execution graph.
- `trace_ui_event_schema.json` – JSON Schema for dashboard event streaming.
- `src/validators.mjs` – reusable validation helpers (AJV + YAML parsing).
- `samples/` – example payloads that exercise the schemas.
- `scripts/validate-samples.mjs` – CLI to validate sample payloads with the helpers.

Usage
-----
1. Install dependencies (from this directory):
   ```
   npm install
   ```
2. Validate bundled samples:
   ```
   npm run validate:samples
   ```
3. Validate a real run directory (expects files like `step_graph.json`, `trace_events.json`, `gold_review.yaml`):
   ```
   npm run validate:run -- path/to/run
   ```
   Or target a run by ID from the shared `workflow_results/runs` root:
   ```
   npm run validate:run-id -- integration-test-TEST12345
   ```
   Set `WORKFLOW_RUNS_ROOT=/absolute/path/to/workflow_results/runs` if the runs live outside the main repository tree.
4. Continuously audit every run artifact directory to catch regressions:
   ```
   python3 ../../scripts/validate_runs_loop.py --watch --interval 300 --include-warnings
   ```
   Pass `--runs-root` if the workflow results live outside the repository (defaults to the shared `RUNS_ROOT` constant).
5. Pair artifact validation with the collective-learning health monitor:
   ```
   # From repository root
   python3 scripts/monitor_collective_learning.py --watch --interval 300 --include-manifest
   ```
   This executes the EventRelay integration tests on each pass and appends structured JSON lines to `collective_learning_monitor_log.jsonl`.
4. Use the helpers in agents/runtime code:
   ```js
   import {
     validateStepGraph,
     validateTraceEvents,
     loadGoldSetEvaluationFromFile,
   } from "./src/validators.mjs";

   // Throws if payload is invalid.
   validateStepGraph(stepGraphPayload);
   validateTraceEvents(eventBatch);
   const gold = loadGoldSetEvaluationFromFile(pathToYaml);
   ```

Integrating With Agents
-----------------------
- Context/Orchestration services should call `validateStepGraph` before publishing or storing execution payloads.
- Telemetry pipelines should wrap outbound event batches with `validateTraceEvents` to enforce schema compliance.
- QA tooling can load run reviews via `loadGoldSetEvaluationFromFile` and persist enriched notes back to storage.

To adapt the schemas for new fields, update the JSON Schema documents first, regenerate supporting samples, and rerun `npm run validate:samples` to ensure coverage.
