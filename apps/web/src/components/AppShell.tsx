'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState, type MouseEvent, type ReactNode } from 'react';
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  Clapperboard,
  CreditCard,
  Film,
  LayoutGrid,
  LogIn,
  PanelLeftClose,
  PanelLeftOpen,
  Plug,
  Plus,
  Sparkles,
} from 'lucide-react';
import { ThemeBar } from '@/components/Nav';
import '@/styles/theme-tokens.css';
import '@/styles/app-shell.css';

const DASHBOARD_STORAGE_KEY = 'eventrelay-dashboard-v1';
const MAX_RECENT_RUNS = 5;

export type RecentRun = { id: string; title: string; url: string };

/**
 * Real local runs only. Reads the persisted Studio store defensively and never
 * invents entries: a fresh browser returns an empty list.
 */
export function readRecentRuns(): RecentRun[] {
  try {
    if (typeof window === 'undefined') return [];
    const raw = window.localStorage.getItem(DASHBOARD_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as { state?: { videos?: unknown } } | null;
    const videos = parsed?.state?.videos;
    if (!Array.isArray(videos)) return [];
    const runs: RecentRun[] = [];
    for (const entry of videos) {
      if (!entry || typeof entry !== 'object') continue;
      const row = entry as Record<string, unknown>;
      if (
        typeof row.id === 'string' &&
        typeof row.title === 'string' &&
        typeof row.url === 'string' &&
        row.title.trim()
      ) {
        runs.push({ id: row.id, title: row.title.trim(), url: row.url });
      }
      if (runs.length >= MAX_RECENT_RUNS) break;
    }
    return runs;
  } catch {
    return [];
  }
}

interface AppShellProps {
  children: ReactNode;
  /** Collapse the sidebar to its 56px icon dock initially. */
  defaultCollapsed?: boolean;
}

/**
 * Unified Webflow/Supercomputer-style left sidebar. It reuses the existing
 * `.uvai-rail-shell` layout contract in theme-tokens.css (page padding,
 * 600-960px icon dock, <600px flattened row) so every route keeps one rhythm.
 */
export default function AppShell({ children, defaultCollapsed = false }: AppShellProps) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const [userToggled, setUserToggled] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [runs, setRuns] = useState<RecentRun[]>([]);

  useEffect(() => {
    setRuns(readRecentRuns());
  }, []);

  useEffect(() => {
    if (
      !defaultCollapsed &&
      typeof window !== 'undefined' &&
      window.innerWidth >= 600 &&
      window.innerWidth <= 960
    ) {
      setCollapsed(true);
    }
  }, [defaultCollapsed]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === '/') {
        event.preventDefault();
        setUserToggled(true);
        setCollapsed((value) => !value);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const toggleCollapsed = () => {
    setUserToggled(true);
    setCollapsed((value) => !value);
  };

  const onNewProject = (event: MouseEvent<HTMLAnchorElement>) => {
    if (pathname !== '/') return;
    const dock = document.getElementById('home-dock-input');
    if (!dock) return;
    event.preventDefault();
    dock.focus();
  };

  const studioActive = pathname === '/studio' || pathname.startsWith('/studio/');
  const pricingActive = pathname === '/pricing';
  const docsActive = pathname === '/docs/api' || pathname.startsWith('/docs/');

  return (
    <>
      <nav
        className="uvai-rail-shell uvai-app-shell-rail template-nav"
        data-collapsed={collapsed ? 'true' : 'false'}
        data-user-toggled={userToggled ? 'true' : 'false'}
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
            onClick={toggleCollapsed}
            aria-expanded={!collapsed}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className="uvai-rail-toggle"
          >
            {collapsed ? (
              <PanelLeftOpen className="h-4 w-4" aria-hidden="true" />
            ) : (
              <PanelLeftClose className="h-4 w-4" aria-hidden="true" />
            )}
          </button>
        </div>

        <div className="uvai-rail-links">
          <Link
            href="/"
            onClick={onNewProject}
            aria-current={pathname === '/' ? 'page' : undefined}
            className="uvai-rail-link"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            <span className="uvai-rail-label">New project</span>
          </Link>
          <Link
            href="/studio"
            aria-current={studioActive ? 'page' : undefined}
            className="uvai-rail-link"
          >
            <Clapperboard className="h-4 w-4" aria-hidden="true" />
            <span className="uvai-rail-label">Studio</span>
          </Link>
          <Link href="/#showcase" className="uvai-rail-link">
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            <span className="uvai-rail-label">Skills</span>
          </Link>
          <Link href="/docs/api#endpoints" className="uvai-rail-link">
            <Plug className="h-4 w-4" aria-hidden="true" />
            <span className="uvai-rail-label">Connectors</span>
          </Link>
          <Link href="/#showcase" className="uvai-rail-link">
            <LayoutGrid className="h-4 w-4" aria-hidden="true" />
            <span className="uvai-rail-label">Examples</span>
          </Link>

          <button
            type="button"
            className="uvai-rail-link uvai-appshell-more-toggle"
            aria-expanded={moreOpen}
            aria-controls="appshell-more-links"
            onClick={() => setMoreOpen((value) => !value)}
          >
            {moreOpen ? (
              <ChevronUp className="h-4 w-4" aria-hidden="true" />
            ) : (
              <ChevronDown className="h-4 w-4" aria-hidden="true" />
            )}
            <span className="uvai-rail-label">{moreOpen ? 'See less' : 'See more'}</span>
          </button>
          <div id="appshell-more-links" className="uvai-appshell-more-links" hidden={!moreOpen && !collapsed}>
            <Link
              href="/pricing"
              aria-current={pricingActive ? 'page' : undefined}
              className="uvai-rail-link"
            >
              <CreditCard className="h-4 w-4" aria-hidden="true" />
              <span className="uvai-rail-label">Pricing</span>
            </Link>
            <Link
              href="/docs/api"
              aria-current={docsActive ? 'page' : undefined}
              className="uvai-rail-link"
            >
              <BookOpen className="h-4 w-4" aria-hidden="true" />
              <span className="uvai-rail-label">API Docs</span>
            </Link>
          </div>
        </div>

        <section className="uvai-appshell-section" aria-labelledby="appshell-runs-heading">
          <h2 id="appshell-runs-heading" className="uvai-appshell-heading">
            Recent runs
          </h2>
          {runs.length > 0 ? (
            <ul className="uvai-appshell-runs">
              {runs.map((run) => (
                <li key={run.id} className="uvai-appshell-run" title={run.title}>
                  {run.title}
                </li>
              ))}
            </ul>
          ) : (
            <p className="uvai-appshell-empty">No local runs yet</p>
          )}
        </section>

        <div className="uvai-rail-cta">
          <Link href="/pricing" className="uvai-btn uvai-btn-primary w-full py-2 px-5 text-sm">
            Get Pro
          </Link>
        </div>
        <Link
          href="/pricing"
          aria-label="Get Pro"
          title="Get Pro"
          className="uvai-rail-collapsed-cta"
        >
          <Sparkles className="h-4 w-4" aria-hidden="true" />
          <span className="uvai-rail-label">Get Pro</span>
        </Link>
        <Link href="/login" className="uvai-rail-link uvai-appshell-signin">
          <LogIn className="h-4 w-4" aria-hidden="true" />
          <span className="uvai-rail-label">Sign in</span>
        </Link>

        <ThemeBar compact={false} />
      </nav>
      {children}
    </>
  );
}
