'use client';

import { forwardRef, ButtonHTMLAttributes, ReactNode } from 'react';
import { clsx } from 'clsx';
import { LoaderCircle } from 'lucide-react';

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
        'border border-[var(--uvai-accent)] bg-[var(--uvai-accent)] text-white',
        'hover:opacity-90'
      ),
      secondary: clsx(
        'border border-[var(--uvai-border-strong)] bg-[var(--uvai-surface)]',
        'text-[var(--uvai-ink)]',
        'hover:bg-[var(--uvai-bg)]'
      ),
      ghost: clsx(
        'bg-transparent text-[var(--uvai-ink-soft)]',
        'hover:bg-[var(--uvai-surface)] hover:text-[var(--uvai-ink)]'
      ),
      danger: clsx(
        'border border-red-700 bg-red-700 text-white',
        'hover:bg-red-800'
      ),
      success: clsx(
        'border border-green-800 bg-green-800 text-white',
        'hover:bg-green-900'
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
          <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
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
