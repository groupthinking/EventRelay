"use strict";
'use client';
Object.defineProperty(exports, "__esModule", { value: true });
exports.default = ResultsViewer;
const clsx_1 = require("clsx");
function ResultsViewer({ executions, events, className }) {
    const completed = executions.filter((e) => e.status === 'complete' && e.result);
    if (completed.length === 0)
        return null;
    return (<div className={(0, clsx_1.clsx)('space-y-3', className)}>
      <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider">
        Results
      </h3>

      <div className="space-y-3">
        {completed.map((exec) => {
            const event = events.find((e) => e.id === exec.event_id);
            return (<div key={exec.agent_id} className="p-4 rounded-xl bg-green-500/5 border border-green-500/10">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-medium text-green-400">
                  ✓ {exec.agent_type}
                </span>
                {event && (<span className="text-xs text-white/30">→ {event.title.slice(0, 50)}</span>)}
              </div>
              <pre className="text-xs text-white/60 bg-black/20 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap">
                {JSON.stringify(exec.result, null, 2)}
              </pre>
            </div>);
        })}
      </div>
    </div>);
}
//# sourceMappingURL=ResultsViewer.js.map