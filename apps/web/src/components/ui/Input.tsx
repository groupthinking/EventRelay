'use client';

import { forwardRef, InputHTMLAttributes, ReactNode } from 'react';
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
    const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;

    const baseStyles = clsx(
      'w-full',
      'font-medium',
      'transition-all duration-200',
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
