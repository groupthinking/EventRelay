"use strict";
'use client';
Object.defineProperty(exports, "__esModule", { value: true });
exports.default = TranscriptViewer;
const react_1 = require("react");
const clsx_1 = require("clsx");
function TranscriptViewer({ transcript, className }) {
    const [expanded, setExpanded] = (0, react_1.useState)(false);
    const [searchQuery, setSearchQuery] = (0, react_1.useState)('');
    const paragraphs = transcript.split('\n').filter((p) => p.trim().length > 0);
    const displayParagraphs = expanded ? paragraphs : paragraphs.slice(0, 8);
    const highlight = (text) => {
        if (!searchQuery)
            return text;
        const regex = new RegExp(`(${searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        const parts = text.split(regex);
        return parts.map((part, i) => regex.test(part) ? (<mark key={i} className="bg-primary-500/30 text-primary-300 rounded px-0.5">
          {part}
        </mark>) : (part));
    };
    return (<div className={(0, clsx_1.clsx)('space-y-3', className)}>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider">
          Transcript
        </h3>
        <span className="text-xs text-white/30">{paragraphs.length} lines</span>
      </div>

      {/* Search */}
      <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search transcript..." className="w-full px-3 py-2 text-sm rounded-lg bg-white/[0.03] border border-white/[0.08] text-white placeholder:text-white/25 focus:outline-none focus:border-primary-500/30"/>

      {/* Content */}
      <div className="space-y-2 max-h-96 overflow-y-auto pr-2">
        {displayParagraphs.map((para, i) => (<p key={i} className="text-sm text-white/70 leading-relaxed p-2 rounded-lg hover:bg-white/[0.03] transition-colors">
            <span className="text-white/25 text-xs mr-2 select-none">{i + 1}</span>
            {highlight(para)}
          </p>))}
      </div>

      {paragraphs.length > 8 && (<button onClick={() => setExpanded(!expanded)} className="text-sm text-primary-400 hover:text-primary-300 transition-colors">
          {expanded ? '▲ Show less' : `▼ Show all ${paragraphs.length} lines`}
        </button>)}
    </div>);
}
//# sourceMappingURL=TranscriptViewer.js.map