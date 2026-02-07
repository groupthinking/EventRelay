'use client';

import { forwardRef, HTMLAttributes } from 'react';
import { clsx } from 'clsx';

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
    gradient: 'from-purple-500/20 to-violet-500/20',
    borderColor: 'border-purple-500/30',
    textColor: 'text-purple-400',
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

export interface TopicChipProps extends HTMLAttributes<HTMLButtonElement> {
  topic: typeof SUGGESTED_TOPICS[0];
  onSelect?: (query: string) => void;
}

const TopicChip = forwardRef<HTMLButtonElement, TopicChipProps>(
  ({ topic, onSelect, className, style, ...props }, ref) => {
    return (
      <button
        ref={ref}
        onClick={() => onSelect?.(topic.query)}
        aria-label={`Search for ${topic.label} videos`}
        className={clsx(
          'group inline-flex items-center gap-2.5 px-4 py-2.5',
          'rounded-xl',
          'bg-gradient-to-r',
          topic.gradient,
          'border',
          topic.borderColor,
          'backdrop-blur-sm',
          'transition-all duration-300 ease-out',
          'hover:scale-105 hover:shadow-lg',
          'hover:border-white/20',
          'active:scale-100',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50',
          'motion-reduce:transition-none motion-reduce:transform-none',
          className
        )}
        style={style}
        {...props}
      >
        <span className={clsx(
          'text-lg font-medium',
          topic.iconClassName
        )}>
          {topic.icon}
        </span>
        <span className={clsx(
          'text-sm font-medium',
          topic.textColor,
          'group-hover:text-white transition-colors motion-reduce:transition-none'
        )}>
          {topic.label}
        </span>
      </button>
    );
  }
);

TopicChip.displayName = 'TopicChip';

export interface SuggestedPromptsProps extends HTMLAttributes<HTMLDivElement> {
  onSelectTopic?: (query: string) => void;
  title?: string;
}

const SuggestedPrompts = forwardRef<HTMLDivElement, SuggestedPromptsProps>(
  ({ onSelectTopic, title = 'TRY A SUGGESTED TOPIC:', className, style, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={clsx(
          'w-full max-w-2xl mx-auto',
          'animate-fade-in-up motion-reduce:animate-none motion-reduce:opacity-100',
          className
        )}
        style={{
          ...style,
          animationDelay: '200ms',
          opacity: 0,
          animationFillMode: 'forwards'
        }}
        {...props}
      >
        <p className="text-xs font-semibold tracking-widest text-white/40 mb-4 text-center">
          {title}
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          {SUGGESTED_TOPICS.map((topic, index) => (
            <TopicChip
              key={topic.id}
              topic={topic}
              onSelect={onSelectTopic}
              style={{
                '--animation-delay': `${300 + index * 100}ms`,
                animationDelay: 'var(--animation-delay)',
                animationFillMode: 'forwards',
                opacity: 0
              } as React.CSSProperties}
              className="animate-fade-in-up"
            />
          ))}
        </div>
      </div>
    );
  }
);

SuggestedPrompts.displayName = 'SuggestedPrompts';

export { SuggestedPrompts, TopicChip, SUGGESTED_TOPICS };
