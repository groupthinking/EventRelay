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
      'transition-all duration-200 ease-out',
      'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50',
      'disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none',
      fullWidth && 'w-full'
    );

    const variants = {
      primary: clsx(
        'bg-gradient-to-r from-primary-500 to-primary-600',
        'text-white shadow-lg shadow-primary-500/25',
        'hover:shadow-xl hover:shadow-primary-500/30 hover:-translate-y-0.5',
        'active:translate-y-0'
      ),
      secondary: clsx(
        'bg-white/5 border border-white/10',
        'text-white',
        'hover:bg-white/10 hover:border-white/20',
        'active:bg-white/5'
      ),
      ghost: clsx(
        'bg-transparent',
        'text-white/70',
        'hover:bg-white/5 hover:text-white',
        'active:bg-white/10'
      ),
      danger: clsx(
        'bg-gradient-to-r from-red-500 to-red-600',
        'text-white shadow-lg shadow-red-500/25',
        'hover:shadow-xl hover:shadow-red-500/30 hover:-translate-y-0.5',
        'active:translate-y-0'
      ),
      success: clsx(
        'bg-gradient-to-r from-green-500 to-green-600',
        'text-white shadow-lg shadow-green-500/25',
        'hover:shadow-xl hover:shadow-green-500/30 hover:-translate-y-0.5',
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
        {...props}
      >
        {isLoading ? (
          <svg
            className="animate-spin h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
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
