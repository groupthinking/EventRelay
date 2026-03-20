"use strict";
'use client';
Object.defineProperty(exports, "__esModule", { value: true });
exports.CardFooter = exports.CardContent = exports.CardHeader = exports.Card = void 0;
const react_1 = require("react");
const clsx_1 = require("clsx");
const Card = (0, react_1.forwardRef)(({ className, variant = 'default', padding = 'md', hoverable = false, glowColor, children, ...props }, ref) => {
    const baseStyles = (0, clsx_1.clsx)('rounded-2xl', 'transition-all duration-300 ease-out');
    const variants = {
        default: (0, clsx_1.clsx)('bg-surface-900/60', 'border border-white/[0.08]', 'backdrop-blur-xl', 'hover:bg-surface-900/70'),
        glass: (0, clsx_1.clsx)('bg-white/[0.03]', 'border border-white/[0.08]', 'backdrop-blur-2xl', 'hover:bg-white/[0.05]'),
        gradient: (0, clsx_1.clsx)('bg-gradient-to-br from-white/[0.06] to-white/[0.02]', 'border border-white/[0.08]', 'backdrop-blur-xl', 'hover:from-white/[0.08] hover:to-white/[0.03]'),
        elevated: (0, clsx_1.clsx)('bg-surface-900', 'border border-white/[0.08]', 'shadow-xl shadow-black/25', 'hover:shadow-2xl hover:shadow-black/30'),
    };
    const paddings = {
        none: '',
        sm: 'p-4',
        md: 'p-6',
        lg: 'p-8',
    };
    const hoverStyles = hoverable
        ? (0, clsx_1.clsx)('cursor-pointer', 'hover:border-primary-500/40', 'hover:shadow-xl hover:shadow-primary-500/15', 'hover:-translate-y-1.5', 'active:translate-y-0 active:shadow-lg', 'will-change-transform')
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
    return (<div ref={ref} className={(0, clsx_1.clsx)(baseStyles, variants[variant], paddings[padding], hoverStyles, glowStyles, className)} {...props}>
        {children}
      </div>);
});
exports.Card = Card;
Card.displayName = 'Card';
const CardHeader = (0, react_1.forwardRef)(({ className, title, subtitle, action, children, ...props }, ref) => {
    return (<div ref={ref} className={(0, clsx_1.clsx)('flex items-start justify-between mb-4', className)} {...props}>
        {(title || subtitle) ? (<div>
            {title && <h3 className="text-lg font-semibold text-white">{title}</h3>}
            {subtitle && <p className="text-sm text-white/50 mt-0.5">{subtitle}</p>}
          </div>) : (children)}
        {action && <div className="ml-4">{action}</div>}
      </div>);
});
exports.CardHeader = CardHeader;
CardHeader.displayName = 'CardHeader';
// Card Content component
const CardContent = (0, react_1.forwardRef)(({ className, children, ...props }, ref) => {
    return (<div ref={ref} className={(0, clsx_1.clsx)('', className)} {...props}>
        {children}
      </div>);
});
exports.CardContent = CardContent;
CardContent.displayName = 'CardContent';
// Card Footer component
const CardFooter = (0, react_1.forwardRef)(({ className, children, ...props }, ref) => {
    return (<div ref={ref} className={(0, clsx_1.clsx)('flex items-center gap-3 mt-6 pt-4', 'border-t border-white/[0.08]', className)} {...props}>
        {children}
      </div>);
});
exports.CardFooter = CardFooter;
CardFooter.displayName = 'CardFooter';
//# sourceMappingURL=Card.js.map