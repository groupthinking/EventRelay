'use client';

import { forwardRef, HTMLAttributes, ReactNode } from 'react';
import { clsx } from 'clsx';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info';
  size?: 'sm' | 'md' | 'lg';
  dot?: boolean;
  dotPulse?: boolean;
  icon?: ReactNode;
}

const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      className,
      variant = 'default',
      size = 'md',
      dot = false,
      dotPulse = false,
      icon,
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles = clsx(
      'inline-flex items-center gap-1.5',
      'font-medium rounded-full',
      'whitespace-nowrap'
    );

    const variants = {
      default: 'bg-white/[0.08] text-white/70 border border-white/[0.08]',
      primary: 'bg-primary-500/15 text-primary-400 border border-primary-500/30',
      success: 'bg-green-500/15 text-green-400 border border-green-500/30',
      warning: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30',
      error: 'bg-red-500/15 text-red-400 border border-red-500/30',
      info: 'bg-blue-500/15 text-blue-400 border border-blue-500/30',
    };

    const sizes = {
      sm: 'px-2 py-0.5 text-2xs',
      md: 'px-2.5 py-1 text-xs',
      lg: 'px-3 py-1.5 text-sm',
    };

    const dotColors = {
      default: 'bg-white/50',
      primary: 'bg-primary-400',
      success: 'bg-green-400',
      warning: 'bg-yellow-400',
      error: 'bg-red-400',
      info: 'bg-blue-400',
    };

    return (
      <span
        ref={ref}
        className={clsx(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {dot && (
          <span className="relative flex h-2 w-2">
            {dotPulse && (
              <span
                className={clsx(
                  'animate-ping absolute inline-flex h-full w-full rounded-full opacity-75',
                  dotColors[variant]
                )}
              />
            )}
            <span
              className={clsx(
                'relative inline-flex rounded-full h-2 w-2',
                dotColors[variant]
              )}
            />
          </span>
        )}
        {icon && <span className="text-current">{icon}</span>}
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

export { Badge };
