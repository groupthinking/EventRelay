'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import {
  BookOpen,
  Clapperboard,
  Contrast,
  CreditCard,
  Film,
  Home,
  Menu,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Sparkles,
  Sun,
  User,
  X,
} from 'lucide-react';
import '@/styles/theme-tokens.css';

interface NavProps {
  rightSlot?: React.ReactNode;
  subtitle?: React.ReactNode;
  fixed?: boolean;
  /** 'topbar' (default) or the Webflow floating 'rail'. */
  variant?: 'topbar' | 'rail';
  /** Collapse the floating rail to its 56px icon dock initially. */
  defaultCollapsed?: boolean;
}

const NAV_LINKS = [
  { href: '/', label: 'Home' },
  { href: '/studio', label: 'Studio' },
  { href: '/pricing', label: 'Pricing' },
  { href: '/docs/api', label: 'API Docs' },
];

const NAV_ICONS: Record<string, typeof Home> = {
  '/': Home,
  '/studio': Clapperboard,
  '/pricing': CreditCard,
  '/docs/api': BookOpen,
};

function isNavActive(pathname: string, href: string): boolean {
  if (href === '/') return pathname === '/';
  return pathname === href || pathname.startsWith(`${href}/`);
}

const rootAttrListeners = new Set<() => void>();

function subscribeRootAttrs(callback: () => void) {
  rootAttrListeners.add(callback);
  return () => {
    rootAttrListeners.delete(callback);
  };
}

function notifyRootAttrs() {
  rootAttrListeners.forEach((listener) => listener());
}

function getThemeSnapshot(): boolean {
  return typeof document !== 'undefined' && document.documentElement.dataset.theme === 'light';
}

function getContrastSnapshot(): boolean {
  return typeof document !== 'undefined' && document.documentElement.dataset.contrast === 'high';
}

function getServerSnapshot(): boolean {
  return false;
}

function useRootThemeState() {
  const lightMode = useSyncExternalStore(subscribeRootAttrs, getThemeSnapshot, getServerSnapshot);
  const highContrast = useSyncExternalStore(
    subscribeRootAttrs,
    getContrastSnapshot,
    getServerSnapshot,
  );

  const toggleTheme = () => {
    if (typeof document === 'undefined') return;
    document.documentElement.dataset.theme = lightMode ? 'dark' : 'light';
    notifyRootAttrs();
  };

  const toggleContrast = () => {
    if (typeof document === 'undefined') return;
    document.documentElement.dataset.contrast = highContrast ? 'normal' : 'high';
    notifyRootAttrs();
  };

  return { lightMode, highContrast, toggleTheme, toggleContrast };
}

/**
 * Webflow-style utility bar: Light/Dark, High Contrast, and (rail only) the
 * keyboard hint. Compact mode drops the hint cell for the top bar.
 */
function ThemeBar({ compact }: { compact: boolean }) {
  const { lightMode, highContrast, toggleTheme, toggleContrast } = useRootThemeState();
  const themeLabel = lightMode ? 'Switch to dark mode' : 'Switch to light mode';

  return (
    <div className="uvai-theme-bar" data-compact={compact ? 'true' : 'false'}>
      <button
        type="button"
        onClick={toggleTheme}
        aria-label={themeLabel}
        title={themeLabel}
        className="uvai-theme-cell"
      >
        {lightMode ? <Moon className="h-4 w-4" aria-hidden="true" /> : <Sun className="h-4 w-4" aria-hidden="true" />}
        <span className="uvai-rail-label" aria-hidden="true">{lightMode ? 'Dark' : 'Light'}</span>
      </button>
      <button
        type="button"
        onClick={toggleContrast}
        aria-pressed={highContrast}
        title="Toggle high contrast"
        className="uvai-theme-cell"
      >
        <Contrast className="h-4 w-4" aria-hidden="true" />
        <span className="uvai-rail-label">High Contrast</span>
      </button>
      {!compact && (
        <span className="uvai-theme-cell uvai-theme-hint" title="Toggle sidebar">
          <kbd aria-hidden="true">⌘/</kbd>
          <span className="sr-only">Command slash toggles the sidebar</span>
        </span>
      )}
    </div>
  );
}

function RailNav({
  pathname,
  rightSlot,
  subtitle,
  defaultCollapsed = false,
}: Pick<NavProps, 'rightSlot' | 'subtitle' | 'defaultCollapsed'> & { pathname: string }) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const ctaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === '/') {
        event.preventDefault();
        setCollapsed((value) => !value);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const expandToAccount = () => {
    setCollapsed(false);
    if (typeof requestAnimationFrame === 'function') {
      requestAnimationFrame(() => {
        ctaRef.current?.querySelector<HTMLElement>('a, button')?.focus();
      });
    }
  };

  return (
    <nav
      className="uvai-rail-shell template-nav"
      data-collapsed={collapsed ? 'true' : 'false'}
      aria-label="Primary"
    >
      <div className="uvai-rail-header">
        <Link href="/" className="uvai-rail-brand" aria-label="UVAI Home">
          <span className="uvai-rail-brand-mark">
            <Film size={18} aria-hidden="true" />
          </span>
          <span className="uvai-rail-brand-text text-lg">UVAI</span>
        </Link>
        <button
          type="button"
          onClick={() => setCollapsed((value) => !value)}
          aria-expanded={!collapsed}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="uvai-rail-toggle"
        >
          {collapsed ? <PanelLeftOpen className="h-4 w-4" aria-hidden="true" /> : <PanelLeftClose className="h-4 w-4" aria-hidden="true" />}
        </button>
      </div>

      {subtitle && !collapsed && (
        <span className="uvai-rail-subtitle px-4 pt-3 text-sm" style={{ color: 'var(--uvai-ink-soft)' }}>{subtitle}</span>
      )}

      <div className="uvai-rail-links">
        {NAV_LINKS.map(({ href, label }) => {
          const Icon = NAV_ICONS[href];
          const active = isNavActive(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? 'page' : undefined}
              className="uvai-rail-link"
            >
              {Icon && <Icon className="h-4 w-4" aria-hidden="true" />}
              <span className="uvai-rail-label">{label}</span>
            </Link>
          );
        })}
      </div>

      <div ref={ctaRef} className="uvai-rail-cta">
        {rightSlot || (
          <Link href="/#get-pro" className="uvai-btn uvai-btn-primary w-full py-2 px-5 text-sm">
            Get Pro
          </Link>
        )}
      </div>

      {collapsed && (
        rightSlot ? (
          <button
            type="button"
            onClick={expandToAccount}
            aria-label="Sign in or account"
            aria-expanded={false}
            title="Sign in / Account"
            className="uvai-rail-collapsed-cta"
          >
            <User className="h-4 w-4" aria-hidden="true" />
            <span className="uvai-rail-label">Sign in</span>
          </button>
        ) : (
          <Link
            href="/#get-pro"
            aria-label="Get Pro"
            title="Get Pro"
            className="uvai-rail-collapsed-cta"
          >
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            <span className="uvai-rail-label">Get Pro</span>
          </Link>
        )
      )}

      <ThemeBar compact={false} />
    </nav>
  );
}

/**
 * Top bar (default) or Webflow floating rail. Obsidian default with a Webflow-style
 * theme bar (light/dark + high contrast).
 */
export default function Nav({
  rightSlot,
  subtitle,
  fixed = false,
  variant = 'topbar',
  defaultCollapsed = false,
}: NavProps) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  if (variant === 'rail') {
    return (
      <RailNav
        pathname={pathname}
        rightSlot={rightSlot}
        subtitle={subtitle}
        defaultCollapsed={defaultCollapsed}
      />
    );
  }

  return (
    <nav
      className="template-nav flex flex-wrap items-center justify-between gap-2 px-3 min-[600px]:px-5 lg:px-10 py-2 min-[901px]:py-3 z-50"
      style={{
        borderBottom: '1px solid var(--uvai-border)',
        background: 'var(--uvai-bg)',
        position: fixed ? 'fixed' : undefined,
        top: fixed ? 0 : undefined,
        left: fixed ? 0 : undefined,
        right: fixed ? 0 : undefined,
      }}
    >
      <div className="flex min-w-0 items-center gap-3 md:gap-5">
        <Link href="/" className="flex shrink-0 items-center gap-2">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-semibold text-sm"
            style={{ background: 'var(--uvai-accent)' }}
          >
            <Film size={18} aria-hidden="true" />
          </div>
          <span className="font-semibold text-lg tracking-tight" style={{ color: 'var(--uvai-ink)' }}>
            UVAI
          </span>
        </Link>

        {subtitle && (
          <span className="hidden lg:inline text-sm whitespace-nowrap" style={{ color: 'var(--uvai-ink-soft)' }}>{subtitle}</span>
        )}

        <div className="hidden min-[600px]:flex items-center gap-0.5 sm:gap-1">
          {NAV_LINKS.map(({ href, label }) => {
            const active = isNavActive(pathname, href);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? 'page' : undefined}
                className="whitespace-nowrap text-xs sm:text-sm px-2 sm:px-2.5 lg:px-3 py-1.5 sm:py-2 rounded-lg transition-colors"
                style={{
                  color: active ? 'var(--uvai-ink)' : 'var(--uvai-ink-soft)',
                  background: active ? 'var(--uvai-surface-warm)' : 'transparent',
                }}
              >
                {label}
              </Link>
            );
          })}
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        <ThemeBar compact />
        {rightSlot || (
          <Link href="/#get-pro" className="uvai-btn uvai-btn-primary whitespace-nowrap !py-2 !px-3.5 sm:!px-4 lg:!px-5 text-xs sm:text-sm">
            Get Pro
          </Link>
        )}
        <button
          type="button"
          onClick={() => setMobileOpen((open) => !open)}
          aria-expanded={mobileOpen}
          aria-controls="mobile-nav"
          aria-label={mobileOpen ? 'Close navigation menu' : 'Open navigation menu'}
          className="min-[600px]:hidden inline-flex items-center justify-center w-9 h-9 rounded-lg"
          style={{ color: 'var(--uvai-ink-soft)' }}
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {mobileOpen && (
        <div id="mobile-nav" className="min-[600px]:hidden w-full mt-2 flex flex-col gap-1 pt-2" style={{ borderTop: '1px solid var(--uvai-border)' }}>
          {NAV_LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setMobileOpen(false)}
              aria-current={isNavActive(pathname, href) ? 'page' : undefined}
              className="text-sm px-3 py-2.5 rounded-lg"
              style={{ color: isNavActive(pathname, href) ? 'var(--uvai-ink)' : 'var(--uvai-ink-soft)' }}
            >
              {label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  );
}
