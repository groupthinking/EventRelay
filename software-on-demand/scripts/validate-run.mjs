import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import {
  validateStepGraph,
  validateTraceEvents,
  loadGoldSetEvaluationFromFile,
} from "../src/validators.mjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function usage() {
  console.error(
    "Usage: node scripts/validate-run.mjs <run-directory> [--graph step_graph.json] [--events trace_events.json] [--gold gold_review.yaml]"
  );
  console.error(
    "   or: node scripts/validate-run.mjs --run-id <run_id> [--graph ...] [--events ...] [--gold ...]"
  );
  process.exit(1);
}

function resolvePath(baseDir, relativePath) {
  if (!relativePath) {
    return null;
  }
  return path.isAbsolute(relativePath)
    ? relativePath
    : path.join(baseDir, relativePath);
}

function parseArgs(argv) {
  const args = [...argv];
  const config = {
    runDir: null,
    runId: null,
    stepGraph: "step_graph.json",
    traceEvents: "trace_events.json",
    goldReview: "gold_review.yaml",
  };

  while (args.length) {
    const token = args.shift();
    switch (token) {
      case "--run-id":
        config.runId = args.shift();
        break;
      case "--graph":
        config.stepGraph = args.shift();
        break;
      case "--events":
        config.traceEvents = args.shift();
        break;
      case "--gold":
        config.goldReview = args.shift();
        break;
      default:
        if (config.runDir === null) {
          config.runDir = token;
        } else {
          console.error(`Unknown argument: ${token}`);
          usage();
        }
    }
  }

  if (!config.runDir && !config.runId) {
    usage();
  }

  return config;
}

function main() {
  const [, , ...rest] = process.argv;
  const config = parseArgs(rest);
  const repoRoot = path.resolve(__dirname, "..", "..", "..", "..");
  const runsRoot = path.resolve(
    process.env.WORKFLOW_RUNS_ROOT ||
      process.env.RUNS_ROOT ||
      path.join(repoRoot, "workflow_results", "runs")
  );

  const candidateDirs = [];

  if (config.runId) {
    candidateDirs.push(path.join(runsRoot, config.runId));
  }

  if (config.runDir) {
    const resolved = path.resolve(config.runDir);
    candidateDirs.push(resolved);
    candidateDirs.push(path.join(runsRoot, config.runDir));
    candidateDirs.push(path.join(repoRoot, config.runDir));
  }

  let baseDir = candidateDirs.find((dir) => fs.existsSync(dir));

  if (!baseDir) {
    console.error(
      "Unable to locate run directory. Checked:\n" + candidateDirs.join("\n")
    );
    process.exit(1);
  }

  let validationsPassed = 0;

  const stepGraphPath = resolvePath(baseDir, config.stepGraph);
  if (stepGraphPath && fs.existsSync(stepGraphPath)) {
    const graph = JSON.parse(fs.readFileSync(stepGraphPath, "utf8"));
    validateStepGraph(graph);
    console.log(`✓ Step graph valid (${stepGraphPath})`);
    validationsPassed += 1;
  } else {
    console.warn(
      `⚠️  Step graph file not found at ${stepGraphPath}; skipping validation.`
    );
  }

  const traceEventsPath = resolvePath(baseDir, config.traceEvents);
  if (traceEventsPath && fs.existsSync(traceEventsPath)) {
    const events = JSON.parse(fs.readFileSync(traceEventsPath, "utf8"));
    validateTraceEvents(events);
    console.log(`✓ Trace events valid (${traceEventsPath})`);
    validationsPassed += 1;
  } else {
    console.warn(
      `⚠️  Trace events file not found at ${traceEventsPath}; skipping validation.`
    );
  }

  const goldReviewPath = resolvePath(baseDir, config.goldReview);
  if (goldReviewPath && fs.existsSync(goldReviewPath)) {
    loadGoldSetEvaluationFromFile(goldReviewPath);
    console.log(`✓ Gold-set evaluation valid (${goldReviewPath})`);
    validationsPassed += 1;
  } else {
    console.warn(
      `⚠️  Gold-set evaluation not found at ${goldReviewPath}; skipping validation.`
    );
  }

  if (validationsPassed === 0) {
    console.error("No validations executed; ensure run artifacts exist.");
    process.exitCode = 1;
  }
}

main();
