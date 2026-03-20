"use strict";
'use client';
Object.defineProperty(exports, "__esModule", { value: true });
exports.default = EventList;
const clsx_1 = require("clsx");
const TYPE_STYLES = {
    action: { bg: 'bg-blue-500/10 border-blue-500/20', text: 'text-blue-400', icon: '⚡' },
    mention: { bg: 'bg-purple-500/10 border-purple-500/20', text: 'text-purple-400', icon: '💬' },
    topic: { bg: 'bg-green-500/10 border-green-500/20', text: 'text-green-400', icon: '📌' },
    insight: { bg: 'bg-amber-500/10 border-amber-500/20', text: 'text-amber-400', icon: '💡' },
};
function EventList({ events, loading, onExtract, className }) {
    if (loading) {
        return (<div className={(0, clsx_1.clsx)('space-y-3', className)}>
        <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider">
          Extracted Events
        </h3>
        <div className="flex items-center gap-2 text-sm text-white/40 py-8 justify-center">
          <span className="animate-spin">⏳</span> Extracting events…
        </div>
      </div>);
    }
    return (<div className={(0, clsx_1.clsx)('space-y-3', className)}>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider">
          Extracted Events
        </h3>
        {events.length === 0 && onExtract && (<button onClick={onExtract} className="text-xs px-3 py-1.5 rounded-lg bg-primary-500/10 text-primary-400 border border-primary-500/20 hover:bg-primary-500/20 transition-colors">
            Extract Events
          </button>)}
        {events.length > 0 && (<span className="text-xs text-white/30">{events.length} events</span>)}
      </div>

      {events.length === 0 && !onExtract && (<p className="text-sm text-white/30 py-4 text-center">No events extracted yet.</p>)}

      <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
        {events.map((event) => {
            const style = TYPE_STYLES[event.type] || TYPE_STYLES.topic;
            return (<div key={event.id} className={(0, clsx_1.clsx)('p-3 rounded-xl border transition-colors hover:bg-white/[0.02]', style.bg)}>
              <div className="flex items-start gap-2">
                <span className="text-base mt-0.5">{style.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={(0, clsx_1.clsx)('text-xs font-semibold uppercase', style.text)}>
                      {event.type}
                    </span>
                    {event.timestamp && (<span className="text-xs text-white/25">{event.timestamp}</span>)}
                  </div>
                  <p className="text-sm text-white/80 mt-1 leading-snug">{event.title}</p>
                  {event.description && (<p className="text-xs text-white/40 mt-1 line-clamp-2">
                      {event.description}
                    </p>)}
                </div>
                <span className="text-xs text-white/20 tabular-nums" title={`Confidence: ${Math.round(event.confidence * 100)}%`}>
                  {Math.round(event.confidence * 100)}%
                </span>
              </div>
            </div>);
        })}
      </div>
    </div>);
}
//# sourceMappingURL=EventList.js.map