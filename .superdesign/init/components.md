# Shared UI primitives

Captured from the production-linked EventRelay source at commit dd3c8a4. These are the complete current primitive implementations Superdesign must preserve when reproducing the baseline.

## apps/web/src/components/ui/Badge.tsx

```tsx
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
                  'animate-ping motion-reduce:animate-none absolute inline-flex h-full w-full rounded-full opacity-75',
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
```

## apps/web/src/components/ui/Button.tsx

```tsx
'use client';

import { forwardRef, ButtonHTMLAttributes, ReactNode } from 'react';
import { clsx } from 'clsx';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'success';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  isLoading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  fullWidth?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      fullWidth = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles = clsx(
      'inline-flex items-center justify-center gap-2',
      'font-semibold rounded-xl',
      'transition-[transform,box-shadow,background-color,border-color,color] duration-200 ease-out',
      'motion-reduce:transition-none',
      'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50',
      'disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none',
      fullWidth && 'w-full'
    );

    const variants = {
      primary: clsx(
        'bg-gradient-to-r from-primary-500 via-primary-600 to-primary-500 bg-[length:200%_100%]',
        'text-white shadow-lg shadow-primary-500/30',
        'hover:shadow-xl hover:shadow-primary-500/40 hover:-translate-y-0.5 motion-reduce:hover:translate-y-0',
        'hover:bg-[position:100%_0]',
        'active:translate-y-0 active:shadow-lg'
      ),
      secondary: clsx(
        'bg-white/[0.04] border border-white/[0.1]',
        'text-white/90',
        'hover:bg-white/[0.08] hover:border-white/[0.2] hover:text-white',
        'active:bg-white/[0.05]'
      ),
      ghost: clsx(
        'bg-transparent',
        'text-white/70',
        'hover:bg-white/[0.06] hover:text-white',
        'active:bg-white/[0.08]'
      ),
      danger: clsx(
        'bg-gradient-to-r from-red-500 via-red-600 to-red-500 bg-[length:200%_100%]',
        'text-white shadow-lg shadow-red-500/30',
        'hover:shadow-xl hover:shadow-red-500/40 hover:-translate-y-0.5 motion-reduce:hover:translate-y-0',
        'hover:bg-[position:100%_0]',
        'active:translate-y-0'
      ),
      success: clsx(
        'bg-gradient-to-r from-green-500 via-green-600 to-green-500 bg-[length:200%_100%]',
        'text-white shadow-lg shadow-green-500/30',
        'hover:shadow-xl hover:shadow-green-500/40 hover:-translate-y-0.5 motion-reduce:hover:translate-y-0',
        'hover:bg-[position:100%_0]',
        'active:translate-y-0'
      ),
    };

    const sizes = {
      sm: 'px-3 py-1.5 text-xs',
      md: 'px-4 py-2 text-sm',
      lg: 'px-6 py-3 text-base',
      xl: 'px-8 py-4 text-lg',
    };

    return (
      <button
        ref={ref}
        className={clsx(baseStyles, variants[variant], sizes[size], className)}
        disabled={disabled || isLoading}
        aria-busy={isLoading || undefined}
        {...props}
      >
        {isLoading ? (
          <svg
            className="animate-spin h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        ) : (
          leftIcon
        )}
        {children}
        {!isLoading && rightIcon}
      </button>
    );
  }
);

Button.displayName = 'Button';

export { Button };
```

## apps/web/src/components/ui/Card.tsx

```tsx
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
```

## apps/web/src/components/ui/Input.tsx

```tsx
'use client';

import { forwardRef, InputHTMLAttributes, ReactNode, useId } from 'react';
import { clsx } from 'clsx';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  variant?: 'default' | 'ghost' | 'filled';
  inputSize?: 'sm' | 'md' | 'lg';
  error?: boolean;
  errorMessage?: string;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  label?: string;
  helperText?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      variant = 'default',
      inputSize = 'md',
      error = false,
      errorMessage,
      leftIcon,
      rightIcon,
      label,
      helperText,
      id,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const inputId = id || generatedId;
    const descriptionId =
      helperText || errorMessage ? `${inputId}-description` : undefined;

    const baseStyles = clsx(
      'w-full',
      'font-medium',
      'transition-[background-color,border-color,box-shadow] duration-200 motion-reduce:transition-none',
      'focus:outline-none',
      'placeholder:text-white/30',
      'disabled:opacity-50 disabled:cursor-not-allowed'
    );

    const variants = {
      default: clsx(
        'bg-surface-900/80 border border-white/[0.1]',
        'hover:border-white/[0.15] hover:bg-surface-900/90',
        'focus:border-primary-500/60 focus:ring-2 focus:ring-primary-500/25',
        'focus:bg-surface-900',
        error && 'border-red-500/50 focus:border-red-500 focus:ring-red-500/20'
      ),
      ghost: clsx(
        'bg-transparent border-b-2 border-white/[0.1] rounded-none',
        'hover:border-white/[0.2]',
        'focus:border-primary-500',
        error && 'border-red-500/50 focus:border-red-500'
      ),
      filled: clsx(
        'bg-white/[0.06] border border-transparent',
        'hover:bg-white/[0.08]',
        'focus:bg-white/[0.04] focus:border-primary-500/50 focus:ring-2 focus:ring-primary-500/20',
        error && 'bg-red-500/10 focus:border-red-500'
      ),
    };

    const sizes = {
      sm: clsx('text-xs rounded-lg', leftIcon ? 'pl-8 pr-3 py-2' : 'px-3 py-2'),
      md: clsx('text-sm rounded-xl', leftIcon ? 'pl-10 pr-4 py-3' : 'px-4 py-3'),
      lg: clsx('text-base rounded-xl', leftIcon ? 'pl-12 pr-5 py-4' : 'px-5 py-4'),
    };

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-white/70 mb-2"
          >
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40">
              {leftIcon}
            </div>
          )}
          <input
            ref={ref}
            id={inputId}
            aria-invalid={error || undefined}
            aria-describedby={descriptionId}
            className={clsx(
              baseStyles,
              variants[variant],
              sizes[inputSize],
              'text-white',
              className
            )}
            {...props}
          />
          {rightIcon && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40">
              {rightIcon}
            </div>
          )}
        </div>
        {(helperText || errorMessage) && (
          <p
            id={descriptionId}
            role={error ? 'alert' : undefined}
            aria-live={error ? 'assertive' : 'polite'}
            className={clsx(
              'mt-2 text-xs',
              error ? 'text-red-400' : 'text-white/40'
            )}
          >
            {error ? errorMessage : helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export { Input };
```

## apps/web/src/components/ui/index.ts

```ts
// Premium UI Components Library
// UVAI.io Design System

export { Button } from './Button';
export type { ButtonProps } from './Button';

export { Card, CardHeader, CardContent, CardFooter } from './Card';
export type { CardProps, CardHeaderProps } from './Card';

export { Badge } from './Badge';
export type { BadgeProps } from './Badge';

export { Input } from './Input';
export type { InputProps } from './Input';

export { SuggestedPrompts, TopicChip, SUGGESTED_TOPICS } from './SuggestedPrompts';
export type { SuggestedPromptsProps, TopicChipProps } from './SuggestedPrompts';
```
