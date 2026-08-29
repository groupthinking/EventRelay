# Theme and design tokens

## Compact visual summary

UVAI uses a near-black canvas, cool white type, teal/cyan brand accents, muted blue-gray borders, and restrained glass surfaces. The dashboard is information-dense and favors 8–14px radii, compact uppercase labels, monospace evidence rows, and clear semantic states. The redesign should retain this recognizable palette while making verification state, source provenance, and pipeline health first-class. Typography is Inter/Geist Sans with Geist Mono for trace data. Motion must remain subtle and respect reduced-motion preferences.

## apps/web/src/app/globals.css

```css
@import "tailwindcss";
@config "../../tailwind.config.js";

/* ============================================
   UVAI Premium Design System
   ============================================ */

:root {
  /* Core Brand Colors */
  --color-primary: 20 184 166; /* teal-500 */
  --color-primary-light: 45 212 191; /* teal-400 */
  --color-primary-dark: 13 148 136; /* teal-600 */

  --color-accent: 34 211 238; /* cyan-400 */
  --color-accent-dark: 6 182 212; /* cyan-500 */

  /* Semantic Landing Tokens */
  --color-void: 5 5 8; /* near-black page bg */
  --color-ink: 248 245 253; /* near-white text */

  /* Surface Colors */
  --color-surface-50: 248 250 252; /* slate-50 */
  --color-surface-100: 241 245 249; /* slate-100 */
  --color-surface-800: 30 41 59; /* slate-800 */
  --color-surface-900: 15 23 42; /* slate-900 */
  --color-surface-950: 2 6 23; /* slate-950 */

  /* Semantic Colors */
  --color-success: 34 197 94; /* green-500 */
  --color-warning: 250 204 21; /* yellow-400 */
  --color-error: 239 68 68; /* red-500 */
  --color-info: 59 130 246; /* blue-500 */

  /* Glass Effect */
  --glass-bg: rgba(15, 23, 42, 0.7);
  --glass-border: rgba(255, 255, 255, 0.1);
  --glass-blur: 20px;

  /* Shadows */
  --shadow-glow: 0 0 60px -12px rgba(20, 184, 166, 0.4);
  --shadow-card:
    0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
  --shadow-elevated: 0 25px 50px -12px rgba(0, 0, 0, 0.5);

  /* Typography */
  --font-heading: "Space Grotesk", "Inter", system-ui, sans-serif;
  --font-body: "Inter", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", "Fira Code", monospace;

  /* Animation */
  --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-base: 200ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-slow: 300ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-spring: 500ms cubic-bezier(0.34, 1.56, 0.64, 1);
}

/* ============================================
   Base Styles
   ============================================ */

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  font-family: var(--font-body);
  background: rgb(var(--color-surface-950));
  color: white;
  line-height: 1.6;
}

/* ============================================
   Typography
   ============================================ */

h1,
h2,
h3,
h4,
h5,
h6 {
  font-family: var(--font-heading);
  font-weight: 700;
  letter-spacing: 0;
  line-height: 1.2;
}

code,
pre {
  font-family: var(--font-mono);
}

/* ============================================
   Glassmorphism Components
   ============================================ */

.glass {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
}

.glass-hover:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.15);
}

.glass-card {
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.05) 0%,
    rgba(255, 255, 255, 0.02) 100%
  );
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 1rem;
}

/* ============================================
   Gradient Utilities
   ============================================ */

.gradient-primary {
  background: linear-gradient(
    135deg,
    rgb(var(--color-primary)) 0%,
    rgb(var(--color-primary-dark)) 100%
  );
}

.gradient-accent {
  background: linear-gradient(
    135deg,
    rgb(var(--color-primary)) 0%,
    rgb(var(--color-accent)) 100%
  );
}

.gradient-text {
  background: linear-gradient(
    135deg,
    rgb(var(--color-primary-light)) 0%,
    rgb(var(--color-accent)) 100%
  );
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.gradient-border {
  position: relative;
  background: rgb(var(--color-surface-900));
  border-radius: 1rem;
}

.gradient-border::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: linear-gradient(
    135deg,
    rgba(20, 184, 166, 0.5) 0%,
    rgba(34, 211, 238, 0.5) 100%
  );
  -webkit-mask:
    linear-gradient(#fff 0 0) content-box,
    linear-gradient(#fff 0 0);
  mask:
    linear-gradient(#fff 0 0) content-box,
    linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
}

/* ============================================
   Animation Keyframes
   ============================================ */

@keyframes float {
  0%,
  100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-10px);
  }
}

@keyframes pulse-glow {
  0%,
  100% {
    opacity: 1;
    box-shadow: 0 0 20px rgba(20, 184, 166, 0.4);
  }
  50% {
    opacity: 0.8;
    box-shadow: 0 0 40px rgba(20, 184, 166, 0.6);
  }
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

@keyframes gradient-shift {
  0%,
  100% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
}

@keyframes fade-in-up {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes scale-in {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes slide-in-right {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* ============================================
   Animation Utilities
   ============================================ */

.animate-float {
  animation: float 6s ease-in-out infinite;
}

.animate-pulse-glow {
  animation: pulse-glow 2s ease-in-out infinite;
}

.animate-gradient {
  background-size: 200% 200%;
  animation: gradient-shift 8s ease infinite;
}

.animate-fade-in-up {
  animation: fade-in-up 0.5s ease-out forwards;
}

.animate-scale-in {
  animation: scale-in 0.3s ease-out forwards;
}

.animate-slide-in-right {
  animation: slide-in-right 0.4s ease-out forwards;
}

/* Stagger delays */
.delay-100 {
  animation-delay: 100ms;
}
.delay-200 {
  animation-delay: 200ms;
}
.delay-300 {
  animation-delay: 300ms;
}
.delay-400 {
  animation-delay: 400ms;
}
.delay-500 {
  animation-delay: 500ms;
}

/* ============================================
   Interactive States
   ============================================ */

.hover-lift {
  transition:
    transform var(--transition-base),
    box-shadow var(--transition-base);
}

.hover-lift:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-elevated);
}

.hover-scale {
  transition: transform var(--transition-spring);
}

.hover-scale:hover {
  transform: scale(1.02);
}

.hover-glow:hover {
  box-shadow: var(--shadow-glow);
}

/* Focus states */
.focus-ring:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.4);
}

.focus-ring:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.4);
}

/* ============================================
   Button Components
   ============================================ */

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  font-weight: 600;
  font-size: 0.875rem;
  line-height: 1;
  border-radius: 0.75rem;
  transition: all var(--transition-base);
  cursor: pointer;
  border: none;
  text-decoration: none;
}

.btn-primary {
  background: linear-gradient(
    135deg,
    rgb(var(--color-primary)) 0%,
    rgb(var(--color-primary-dark)) 100%
  );
  color: white;
  box-shadow: 0 4px 14px -4px rgba(20, 184, 166, 0.4);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px -8px rgba(20, 184, 166, 0.5);
}

.btn-primary:active {
  transform: translateY(0);
  box-shadow: 0 4px 14px -4px rgba(20, 184, 166, 0.4);
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.05);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

.btn-ghost {
  background: transparent;
  color: rgba(255, 255, 255, 0.7);
}

.btn-ghost:hover {
  background: rgba(255, 255, 255, 0.05);
  color: white;
}

/* ============================================
   Input Components
   ============================================ */

.input {
  width: 100%;
  padding: 0.75rem 1rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.75rem;
  color: white;
  font-size: 0.875rem;
  transition: all var(--transition-base);
}

.input::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.input:focus {
  outline: none;
  border-color: rgb(var(--color-primary));
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.2);
}

/* ============================================
   Card Components
   ============================================ */

.card {
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 1rem;
  padding: 1.5rem;
  transition: all var(--transition-base);
}

.card:hover {
  border-color: rgba(20, 184, 166, 0.3);
  box-shadow: 0 0 40px -10px rgba(20, 184, 166, 0.2);
}

/* ============================================
   Badge Components
   ============================================ */

.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.badge-primary {
  background: rgba(20, 184, 166, 0.15);
  border-color: rgba(20, 184, 166, 0.3);
  color: rgb(var(--color-primary-light));
}

.badge-success {
  background: rgba(34, 197, 94, 0.15);
  border-color: rgba(34, 197, 94, 0.3);
  color: rgb(var(--color-success));
}

.badge-warning {
  background: rgba(250, 204, 21, 0.15);
  border-color: rgba(250, 204, 21, 0.3);
  color: rgb(var(--color-warning));
}

.badge-error {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.3);
  color: rgb(var(--color-error));
}

/* ============================================
   Scrollbar Styling
   ============================================ */

::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}

/* ============================================
   Selection Styling
   ============================================ */

::selection {
  background: rgba(20, 184, 166, 0.3);
  color: white;
}

/* ============================================
   Noise Texture Overlay
   ============================================ */

.noise::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
  opacity: 0.02;
  pointer-events: none;
  z-index: 1;
}

/* ============================================
   Background Mesh Gradient
   ============================================ */

.mesh-gradient,
.bg-mesh {
  background:
    radial-gradient(at 40% 20%, rgba(20, 184, 166, 0.15) 0px, transparent 50%),
    radial-gradient(at 80% 0%, rgba(34, 211, 238, 0.1) 0px, transparent 50%),
    radial-gradient(at 0% 50%, rgba(20, 184, 166, 0.1) 0px, transparent 50%),
    radial-gradient(at 80% 50%, rgba(34, 211, 238, 0.08) 0px, transparent 50%),
    radial-gradient(at 0% 100%, rgba(20, 184, 166, 0.1) 0px, transparent 50%),
    radial-gradient(at 80% 100%, rgba(34, 211, 238, 0.08) 0px, transparent 50%);
}

/* ============================================
   Skeleton Loading (Used by loading states)
   ============================================ */

.skeleton {
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0.03) 0%,
    rgba(255, 255, 255, 0.08) 50%,
    rgba(255, 255, 255, 0.03) 100%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
  border-radius: 0.5rem;
}

@keyframes skeleton-shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

@keyframes landing-marquee {
  from {
    transform: translateX(0);
  }
  to {
    transform: translateX(-50%);
  }
}

.animate-marquee {
  animation: landing-marquee 22s linear infinite;
}

@media (prefers-reduced-motion: reduce) {
  .animate-marquee {
    animation: none;
  }
}

.contact-form-input {
  width: 100%;
  padding: 0.7rem 0.9rem;
  border-radius: 0.55rem;
  background: rgba(14, 14, 19, 0.7);
  border: 1px solid rgba(72, 71, 77, 0.18);
  color: #f8f5fd;
  font-size: 0.9rem;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}

.contact-form-input::placeholder {
  color: rgba(248, 245, 253, 0.3);
}

.contact-form-input:focus {
  outline: none;
  border-color: #6af2de;
  box-shadow: 0 0 0 3px rgba(106, 242, 222, 0.15);
}

select.contact-form-input {
  appearance: none;
  background-image:
    linear-gradient(45deg, transparent 50%, #6af2de 50%),
    linear-gradient(135deg, #6af2de 50%, transparent 50%);
  background-position:
    calc(100% - 18px) 50%,
    calc(100% - 13px) 50%;
  background-size: 5px 5px, 5px 5px;
  background-repeat: no-repeat;
  padding-right: 2.2rem;
}

textarea.contact-form-input {
  resize: vertical;
  min-height: 100px;
}

/* ============================================
   Stitch Dashboard Animations
   ============================================ */

@keyframes stitch-fade-in {
  0% {
    opacity: 0;
    transform: translateY(12px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

.stitch-fade-in {
  animation: stitch-fade-in 0.5s cubic-bezier(0.23, 1, 0.32, 1) both;
}

/* Staggered children — use with style={{ animationDelay }} */
.stitch-fade-in:nth-child(1) { animation-delay: 0ms; }
.stitch-fade-in:nth-child(2) { animation-delay: 80ms; }
.stitch-fade-in:nth-child(3) { animation-delay: 160ms; }
.stitch-fade-in:nth-child(4) { animation-delay: 240ms; }
.stitch-fade-in:nth-child(5) { animation-delay: 320ms; }
.stitch-fade-in:nth-child(6) { animation-delay: 400ms; }

/* ============================================
   Mobile Responsive — Dashboard Split View
   ============================================ */

@media (max-width: 768px) {
  /* Collapse split-view to vertical stack on mobile */
  .flex.flex-1.overflow-hidden {
    flex-direction: column !important;
  }
  .flex.flex-1.overflow-hidden > div:first-child {
    width: 100% !important;
    min-width: unset !important;
    max-height: 45vh;
  }
  .flex.flex-1.overflow-hidden > div:last-child {
    width: 100% !important;
  }
}

/* ============================================
   Mobile Responsive — Landing Page
   ============================================ */

@media (max-width: 640px) {
  /* Product mockup collapses to single column */
  .grid[style*="grid-template-columns: 45% 55%"] {
    grid-template-columns: 1fr !important;
  }
  /* Metrics bar wraps */
  .grid-cols-4 {
    grid-template-columns: repeat(2, 1fr) !important;
  }
}
```

## apps/web/tailwind.config.js

```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Semantic page tokens
        void: 'rgb(var(--color-void))',
        ink: 'rgb(var(--color-ink))',

        // Brand colors
        primary: {
          50: '#f0fdfa',
          100: '#ccfbf1',
          200: '#99f6e4',
          300: '#5eead4',
          400: '#2dd4bf',
          500: '#14b8a6',
          600: '#0d9488',
          700: '#0f766e',
          800: '#115e59',
          900: '#134e4a',
          950: '#042f2e',
        },
        accent: {
          50: '#ecfeff',
          100: '#cffafe',
          200: '#a5f3fc',
          300: '#67e8f9',
          400: '#22d3ee',
          500: '#06b6d4',
          600: '#0891b2',
          700: '#0e7490',
          800: '#155e75',
          900: '#164e63',
        },
        surface: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        heading: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.75rem' }],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
      borderRadius: {
        '4xl': '2rem',
        '5xl': '2.5rem',
      },
      backdropBlur: {
        xs: '2px',
      },
      boxShadow: {
        'glow': '0 0 60px -12px rgba(20, 184, 166, 0.4)',
        'glow-lg': '0 0 80px -12px rgba(20, 184, 166, 0.5)',
        'glow-accent': '0 0 60px -12px rgba(34, 211, 238, 0.4)',
        'inner-glow': 'inset 0 2px 4px 0 rgba(255, 255, 255, 0.06)',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'shimmer': 'shimmer 2s linear infinite',
        'gradient': 'gradient-shift 8s ease infinite',
        'fade-in-up': 'fade-in-up 0.5s ease-out forwards',
        'scale-in': 'scale-in 0.3s ease-out forwards',
        'slide-in-right': 'slide-in-right 0.4s ease-out forwards',
        'spin-slow': 'spin 3s linear infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'pulse-glow': {
          '0%, 100%': {
            opacity: '1',
            boxShadow: '0 0 20px rgba(20, 184, 166, 0.4)',
          },
          '50%': {
            opacity: '0.8',
            boxShadow: '0 0 40px rgba(20, 184, 166, 0.6)',
          },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'gradient-shift': {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        'fade-in-up': {
          from: {
            opacity: '0',
            transform: 'translateY(20px)',
          },
          to: {
            opacity: '1',
            transform: 'translateY(0)',
          },
        },
        'scale-in': {
          from: {
            opacity: '0',
            transform: 'scale(0.95)',
          },
          to: {
            opacity: '1',
            transform: 'scale(1)',
          },
        },
        'slide-in-right': {
          from: {
            opacity: '0',
            transform: 'translateX(20px)',
          },
          to: {
            opacity: '1',
            transform: 'translateX(0)',
          },
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
        'mesh': `
          radial-gradient(at 40% 20%, rgba(20, 184, 166, 0.15) 0px, transparent 50%),
          radial-gradient(at 80% 0%, rgba(34, 211, 238, 0.1) 0px, transparent 50%),
          radial-gradient(at 0% 50%, rgba(20, 184, 166, 0.1) 0px, transparent 50%),
          radial-gradient(at 80% 50%, rgba(34, 211, 238, 0.08) 0px, transparent 50%),
          radial-gradient(at 0% 100%, rgba(20, 184, 166, 0.1) 0px, transparent 50%),
          radial-gradient(at 80% 100%, rgba(34, 211, 238, 0.08) 0px, transparent 50%)
        `,
      },
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
    },
  },
  plugins: [],
};
```
