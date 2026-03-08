const fs = require('fs');

let yml = fs.readFileSync('.github/workflows/pr-checks.yml', 'utf8');
yml = yml.replace('permissions:\n  pull-requests: write', 'permissions:\n  pull-requests: write\n  issues: write');
fs.writeFileSync('.github/workflows/pr-checks.yml', yml);

let yml2 = fs.readFileSync('.github/workflows/auto-label.yml', 'utf8');
yml2 = yml2.replace('permissions:\n  pull-requests: write', 'permissions:\n  pull-requests: write\n  issues: write');
fs.writeFileSync('.github/workflows/auto-label.yml', yml2);
