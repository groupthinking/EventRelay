const fs = require('fs');
const path = require('path');

/**
 * Local maintenance script to patch GitHub workflow permissions.
 *
 * This is intended to be run manually by maintainers (e.g. `node patch2.js`)
 * and MUST NOT be executed in CI. It updates selected workflow files to grant
 * `issues: write` alongside `pull-requests: write`.
 */

const WORKFLOWS_DIR = path.join(__dirname, '.github', 'workflows');
const PERMISSIONS_OLD = 'permissions:\n  pull-requests: write';
const PERMISSIONS_NEW = 'permissions:\n  pull-requests: write\n  issues: write';

function patchWorkflowPermissions(fileName) {
  const workflowPath = path.join(WORKFLOWS_DIR, fileName);
  const original = fs.readFileSync(workflowPath, 'utf8');
  const patched = original.replace(PERMISSIONS_OLD, PERMISSIONS_NEW);
  fs.writeFileSync(workflowPath, patched);
}

function main() {
  // Prevent accidental execution in CI environments.
  if (process.env.CI) {
    console.error('patch2.js must not be run in CI. Aborting without changes.');
    process.exit(1);
  }

  try {
    patchWorkflowPermissions('pr-checks.yml');
    patchWorkflowPermissions('auto-label.yml');
  } catch (error) {
    console.error('Failed to patch workflow permissions:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}
