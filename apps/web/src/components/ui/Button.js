"use strict";
'use client';
Object.defineProperty(exports, "__esModule", { value: true });
exports.Button = void 0;
const react_1 = require("react");
const clsx_1 = require("clsx");
const Button = (0, react_1.forwardRef)(({ className, variant = 'primary', size = 'md', isLoading = false, leftIcon, rightIcon, fullWidth = false, disabled, children, ...props }, ref) => {
    const baseStyles = (0, clsx_1.clsx)('inline-flex items-center justify-center gap-2', 'font-semibold rounded-xl', 'transition-all duration-200 ease-out', 'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50', 'disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none', fullWidth && 'w-full');
    const variants = {
        primary: (0, clsx_1.clsx)('bg-gradient-to-r from-primary-500 via-primary-600 to-primary-500 bg-[length:200%_100%]', 'text-white shadow-lg shadow-primary-500/30', 'hover:shadow-xl hover:shadow-primary-500/40 hover:-translate-y-0.5', 'hover:bg-[position:100%_0]', 'active:translate-y-0 active:shadow-lg', 'transition-all duration-300'),
        secondary: (0, clsx_1.clsx)('bg-white/[0.04] border border-white/[0.1]', 'text-white/90', 'hover:bg-white/[0.08] hover:border-white/[0.2] hover:text-white', 'active:bg-white/[0.05]', 'transition-all duration-200'),
        ghost: (0, clsx_1.clsx)('bg-transparent', 'text-white/70', 'hover:bg-white/[0.06] hover:text-white', 'active:bg-white/[0.08]', 'transition-all duration-200'),
        danger: (0, clsx_1.clsx)('bg-gradient-to-r from-red-500 via-red-600 to-red-500 bg-[length:200%_100%]', 'text-white shadow-lg shadow-red-500/30', 'hover:shadow-xl hover:shadow-red-500/40 hover:-translate-y-0.5', 'hover:bg-[position:100%_0]', 'active:translate-y-0', 'transition-all duration-300'),
        success: (0, clsx_1.clsx)('bg-gradient-to-r from-green-500 via-green-600 to-green-500 bg-[length:200%_100%]', 'text-white shadow-lg shadow-green-500/30', 'hover:shadow-xl hover:shadow-green-500/40 hover:-translate-y-0.5', 'hover:bg-[position:100%_0]', 'active:translate-y-0', 'transition-all duration-300'),
    };
    const sizes = {
        sm: 'px-3 py-1.5 text-xs',
        md: 'px-4 py-2 text-sm',
        lg: 'px-6 py-3 text-base',
        xl: 'px-8 py-4 text-lg',
    };
    return (<button ref={ref} className={(0, clsx_1.clsx)(baseStyles, variants[variant], sizes[size], className)} disabled={disabled || isLoading} {...props}>
        {isLoading ? (<svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
          </svg>) : (leftIcon)}
        {children}
        {!isLoading && rightIcon}
      </button>);
});
exports.Button = Button;
Button.displayName = 'Button';
//# sourceMappingURL=Button.js.map