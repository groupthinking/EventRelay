'use client';

import { forwardRef, HTMLAttributes, ReactNode } from 'react';
import { clsx } from 'clsx';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'glass' | 'gradient' | 'elevated';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hoverable?: boolean;
  glowColor?: 'primary' | 'accent' | 'success' | 'warning' | 'error';
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      className,
      variant = 'default',
      padding = 'md',
      hoverable = false,
      glowColor,
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles = clsx(
      'rounded-2xl',
      'transition-[transform,box-shadow,background-color,border-color] duration-300 ease-out',
      'motion-reduce:transition-none'
    );

    const variants = {
      default: clsx(
        'bg-surface-900/60',
        'border border-white/[0.08]',
        'backdrop-blur-xl',
        'hover:bg-surface-900/70'
      ),
      glass: clsx(
        'bg-white/[0.03]',
        'border border-white/[0.08]',
        'backdrop-blur-2xl',
        'hover:bg-white/[0.05]'
      ),
      gradient: clsx(
        'bg-gradient-to-br from-white/[0.06] to-white/[0.02]',
        'border border-white/[0.08]',
        'backdrop-blur-xl',
        'hover:from-white/[0.08] hover:to-white/[0.03]'
      ),
      elevated: clsx(
        'bg-surface-900',
        'border border-white/[0.08]',
        'shadow-xl shadow-black/25',
        'hover:shadow-2xl hover:shadow-black/30'
      ),
    };

    const paddings = {
      none: '',
      sm: 'p-4',
      md: 'p-6',
      lg: 'p-8',
    };

    const hoverStyles = hoverable
      ? clsx(
          'cursor-pointer',
          'hover:border-primary-500/40',
          'hover:shadow-xl hover:shadow-primary-500/15',
          'hover:-translate-y-1.5 motion-reduce:hover:translate-y-0',
          'active:translate-y-0 active:shadow-lg',
          'will-change-transform'
        )
      : '';

    const glowStyles = glowColor
      ? {
          primary: 'hover:shadow-primary-500/20',
          accent: 'hover:shadow-accent-500/20',
          success: 'hover:shadow-green-500/20',
          warning: 'hover:shadow-yellow-500/20',
          error: 'hover:shadow-red-500/20',
        }[glowColor]
      : '';

    return (
      <div
        ref={ref}
        className={clsx(
          baseStyles,
          variants[variant],
          paddings[padding],
          hoverStyles,
          glowStyles,
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

// Card Header component
export interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
}

const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, title, subtitle, action, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={clsx('flex items-start justify-between mb-4', className)}
        {...props}
      >
        {(title || subtitle) ? (
          <div>
            {title && <h3 className="text-lg font-semibold text-white">{title}</h3>}
            {subtitle && <p className="text-sm text-white/50 mt-0.5">{subtitle}</p>}
          </div>
        ) : (
          children
        )}
        {action && <div className="ml-4">{action}</div>}
      </div>
    );
  }
);

CardHeader.displayName = 'CardHeader';

// Card Content component
const CardContent = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => {
    return (
      <div ref={ref} className={clsx('', className)} {...props}>
        {children}
      </div>
    );
  }
);

CardContent.displayName = 'CardContent';

// Card Footer component
const CardFooter = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={clsx(
          'flex items-center gap-3 mt-6 pt-4',
          'border-t border-white/[0.08]',
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

CardFooter.displayName = 'CardFooter';

export { Card, CardHeader, CardContent, CardFooter };
