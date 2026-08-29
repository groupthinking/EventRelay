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
