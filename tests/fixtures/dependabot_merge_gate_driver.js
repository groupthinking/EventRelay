// Test driver for the Dependabot auto-merge `merge` job.
//
// The job body is inline JavaScript inside a workflow YAML file, so the only
// way to test its *behaviour* (rather than assert that it contains certain
// words) is to extract the script and run it against a stubbed octokit. This
// driver does that: it takes the extracted script and a JSON scenario, and
// reports whether the gate merged, plus the reason it logged.
//
// Usage: node dependabot_merge_gate_driver.js <script.js> <scenario.json>
// Output (stdout, JSON): {"merged": bool, "log": [string, ...]}

const fs = require("fs");

const script = fs.readFileSync(process.argv[2], "utf8");
const scenario = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));

const HEAD_SHA = "0000000000000000000000000000000000000000";
const log = [];
let merged = false;

const github = {
  // Only the pre-fix script calls `github.request`; keep it present so that
  // version fails on its own logic rather than on a missing stub.
  request: async () => ({ data: { number: 1, ...(scenario.pullsGetExtra || {}) } }),
  rest: {
    pulls: {
      get: async () => ({
        data: {
          number: 1,
          head: { sha: HEAD_SHA },
          user: { login: scenario.author || "dependabot[bot]" },
          draft: scenario.draft === true,
        },
      }),
      merge: async () => {
        merged = true;
      },
    },
    repos: {
      getCommit: async () => ({
        data: { commit: { message: scenario.commitMessage || "" } },
      }),
      getCombinedStatusForRef: async () => ({
        data: { state: scenario.combinedState || "success" },
      }),
    },
    checks: { listForRef: "listForRef" },
  },
  paginate: async () => scenario.checkRuns || [],
};

const context = {
  repo: { owner: "groupthinking", repo: "EventRelay" },
  payload: {
    check_suite: { head_sha: HEAD_SHA, pull_requests: [{ number: 1 }] },
  },
};

const core = {
  info: (message) => log.push(String(message)),
  notice: (message) => log.push(String(message)),
};

const run = new Function(
  "github",
  "context",
  "core",
  `return (async () => {${script}})()`,
);

run(github, context, core)
  .then(() => process.stdout.write(JSON.stringify({ merged, log })))
  .catch((error) => {
    process.stderr.write(String((error && error.stack) || error));
    process.exit(1);
  });
