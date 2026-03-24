"use strict";
'use client';
Object.defineProperty(exports, "__esModule", { value: true });
exports.SUGGESTED_TOPICS = exports.TopicChip = exports.SuggestedPrompts = void 0;
const react_1 = require("react");
const clsx_1 = require("clsx");
// Topic data with icons (using text-based icons for consistency)
const SUGGESTED_TOPICS = [
    {
        id: 'photosynthesis',
        label: 'Photosynthesis',
        icon: '🌿',
        gradient: 'from-green-500/20 to-emerald-500/20',
        borderColor: 'border-green-500/30',
        textColor: 'text-green-400',
        query: 'photosynthesis explained'
    },
    {
        id: 'fermi-paradox',
        label: 'Fermi Paradox',
        icon: '👽',
        gradient: 'from-sky-500/20 to-indigo-500/20',
        borderColor: 'border-sky-500/30',
        textColor: 'text-sky-400',
        query: 'fermi paradox'
    },
    {
        id: 'french-revolution',
        label: 'French Revolution',
        icon: '🏛️',
        gradient: 'from-red-500/20 to-orange-500/20',
        borderColor: 'border-red-500/30',
        textColor: 'text-red-400',
        query: 'french revolution history'
    },
    {
        id: 'engines',
        label: 'How Engines Work',
        icon: '⚙️',
        gradient: 'from-blue-500/20 to-cyan-500/20',
        borderColor: 'border-blue-500/30',
        textColor: 'text-blue-400',
        query: 'how engines work'
    },
    {
        id: 'ancient-greece',
        label: 'Ancient Greece',
        icon: 'Λ',
        gradient: 'from-amber-500/20 to-yellow-500/20',
        borderColor: 'border-amber-500/30',
        textColor: 'text-amber-400',
        query: 'ancient greek philosophy'
    },
];
exports.SUGGESTED_TOPICS = SUGGESTED_TOPICS;
const TopicChip = (0, react_1.forwardRef)(({ topic, onSelect, className, style, ...props }, ref) => {
    return (<button ref={ref} onClick={() => onSelect?.(topic.query)} aria-label={`Search for ${topic.label} videos`} className={(0, clsx_1.clsx)('group inline-flex items-center gap-2.5 px-4 py-2.5', 'rounded-xl', 'bg-gradient-to-r', topic.gradient, 'border', topic.borderColor, 'backdrop-blur-sm', 'transition-all duration-300 ease-out', 'hover:scale-105 hover:shadow-lg', 'hover:border-white/20', 'active:scale-100', 'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50', 'motion-reduce:transition-none motion-reduce:transform-none', className)} style={style} {...props}>
        <span className={(0, clsx_1.clsx)('text-lg font-medium')}>
          {topic.icon}
        </span>
        <span className={(0, clsx_1.clsx)('text-sm font-medium', topic.textColor, 'group-hover:text-white transition-colors motion-reduce:transition-none')}>
          {topic.label}
        </span>
      </button>);
});
exports.TopicChip = TopicChip;
TopicChip.displayName = 'TopicChip';
const SuggestedPrompts = (0, react_1.forwardRef)(({ onSelectTopic, title = 'TRY A SUGGESTED TOPIC:', className, style, ...props }, ref) => {
    return (<div ref={ref} className={(0, clsx_1.clsx)('w-full max-w-2xl mx-auto', 'animate-fade-in-up motion-reduce:animate-none motion-reduce:opacity-100', className)} style={{
            ...style,
            animationDelay: '200ms',
            opacity: 0,
            animationFillMode: 'forwards'
        }} {...props}>
        <p className="text-xs font-semibold tracking-widest text-white/40 mb-4 text-center">
          {title}
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          {SUGGESTED_TOPICS.map((topic, index) => (<TopicChip key={topic.id} topic={topic} onSelect={onSelectTopic} style={{
                animationDelay: `${300 + index * 100}ms`,
                animationFillMode: 'forwards',
                opacity: 0
            }} className="animate-fade-in-up motion-reduce:animate-none motion-reduce:opacity-100"/>))}
        </div>
      </div>);
});
exports.SuggestedPrompts = SuggestedPrompts;
SuggestedPrompts.displayName = 'SuggestedPrompts';
//# sourceMappingURL=SuggestedPrompts.js.map