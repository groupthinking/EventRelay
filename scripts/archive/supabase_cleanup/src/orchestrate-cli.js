"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const orchestrator_1 = require("./orchestrator");
(0, orchestrator_1.orchestrate)('cli').then(summary => {
    console.log('Orchestration summary:', summary);
    process.exit(0);
}).catch(err => {
    console.error('Orchestration error:', err);
    process.exit(1);
});
//# sourceMappingURL=orchestrate-cli.js.map