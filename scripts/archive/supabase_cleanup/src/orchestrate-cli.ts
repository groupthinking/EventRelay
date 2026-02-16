import { orchestrate } from './orchestrator';

orchestrate('cli').then(summary => {
  console.log('Orchestration summary:', summary);
  process.exit(0);
}).catch(err => {
  console.error('Orchestration error:', err);
  process.exit(1);
}); 