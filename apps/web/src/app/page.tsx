import type { Metadata } from 'next';
import Link from 'next/link';
import {
  Bot,
  Film,
  FileText,
  Layers,
  LayoutTemplate,
  Plug,
  ScrollText,
  Workflow,
  Wrench,
} from 'lucide-react';
import Nav from '@/components/Nav';
import Footer from '@/components/Footer';
import HomePasteForm from '@/components/home/HomePasteForm';
import HomeTemplateShell from '@/components/home/HomeTemplateShell';
import '@/components/home/home-template.css';
import '@/styles/home-shipper.css';
import {
  WORKFLOW_PRO_PRODUCT_NAME,
  workflowProPriceLabel,
} from '@/lib/billing/checkout-config';
import { customBadge } from '@/flags';

export const metadata: Metadata = {
  title: 'UVAI — YouTube videos to bound tasks',
  description:
    'Bind YouTube videos to source-linked tasks, expected outputs, and proposed checks in Studio. Transcript quality varies by source.',
  alternates: { canonical: '/' },
};

const OFFERS = [
  {
    name: WORKFLOW_PRO_PRODUCT_NAME,
    price: `${workflowProPriceLabel(false)} · ${workflowProPriceLabel(true)}`,
  },
  {
    name: 'Ship',
    price: 'per-job quote',
  },
  {
    name: 'Maintain',
    price: '$199/mo',
  },
] as const;

const SHOWCASE = [
  {
    Icon: FileText,
    title: 'Software tutorial',
    note: 'Inspect steps and prerequisites',
    eyebrow: '01 · VIDEO PACK',
    pill: 'Timed Captions',
    stageHeadline: 'Extract Tasks.',
    stageAccent: 'Instantly.',
    tone: 'emerald',
  },
  {
    Icon: Layers,
    title: 'Product walkthrough',
    note: 'Review features and interactions',
    eyebrow: '02 · STACK MAP',
    pill: 'Next.js · Shopify',
    stageHeadline: 'Wired to Real',
    stageAccent: 'Starter Kits.',
    tone: 'violet',
  },
  {
    Icon: Workflow,
    title: 'Process recording',
    note: 'Explore proposed work',
    eyebrow: '03 · LIVE SANDBOX',
    pill: '/d/ Preview',
    stageHeadline: 'Every Check',
    stageAccent: 'Source-Linked.',
    tone: 'cobalt',
  },
] as const;

const PROCESS_TILES = [
  {
    n: '1',
    Icon: Film,
    title: 'Videos',
    note: 'Timestamps and keyframes stay attached to each task.',
    chips: ['timestamps', 'keyframes'],
    badge: 'CORE',
    tone: 'emerald',
  },
  {
    n: '2',
    Icon: LayoutTemplate,
    title: 'Templates',
    note: 'Starter scaffolds to build from.',
    chips: ['Next.js', 'Shopify CLI'],
    badge: 'STARTERS',
    tone: 'cobalt',
  },
  {
    n: '3',
    Icon: Wrench,
    title: 'Tools & Code',
    note: 'Detected stack plus proposed checks.',
    chips: ['stack', 'checks'],
    badge: 'TRENDING',
    tone: 'hot',
  },
  {
    n: '4',
    Icon: Plug,
    title: 'MCPs & Harnesses',
    note: 'Tool servers wired into the build.',
    chips: ['langextract', 'vercel', 'git-workflow'],
    badge: 'NEW',
    tone: 'emerald',
  },
  {
    n: '5',
    Icon: ScrollText,
    title: 'Prompts & Specs',
    note: 'A spec and planner for each task.',
    chips: ['G.A.T.E. spec', '5-field planner'],
    badge: 'G.A.T.E.',
    tone: 'cobalt',
  },
  {
    n: '6',
    Icon: Bot,
    title: 'Agent Ops',
    note: 'Post-build workflow tracks, not guarantees.',
    chips: ['Build', 'Fix', 'Maintain', 'Run', 'Grow', 'Monetize'],
    badge: 'AI OPS',
    tone: 'hot',
  },
] as const;

const AGENT_FLOW = ['Video', 'Video Pack', 'Tasks', 'Checks', 'Review'] as const;

/**
 * Shipper/Higgsfield pre-login visual showcase hierarchy in UVAI obsidian:
 * 3-card preview strip -> hero bento (emerald/cobalt stage composer + 3x2 badged process tiles)
 * -> compact workflow band -> compact plans CTA strip -> footer.
 */
export default async function HomePage() {
  const showCustomBadge = await customBadge();

  return (
    <main className="min-h-screen overflow-x-clip" style={{ background: 'var(--uvai-bg)' }}>
      <Nav />

      <section aria-labelledby="home-heading" className="template-home home-shipper px-4 sm:px-6 lg:px-10 pb-12 pt-4 sm:pt-6">
        <div className="mx-auto max-w-[1440px]">
          <div className="template-use-cases" aria-label="Supported source examples">
            {SHOWCASE.map(({ Icon, title, note, eyebrow, pill, stageHeadline, stageAccent, tone }) => (
              <div key={title} className="home-showcase-card" data-tone={tone}>
                <div className="home-showcase-stage" aria-hidden="true">
                  <div className="home-showcase-top">
                    <span className="home-showcase-eyebrow">{eyebrow}</span>
                    <span className="home-showcase-pill">{pill}</span>
                  </div>
                  <p className="home-showcase-display">
                    {stageHeadline} <em>{stageAccent}</em>
                  </p>
                </div>
                <div className="home-showcase-meta">
                  <Icon size={16} aria-hidden="true" />
                  <strong>{title}</strong>
                  <span>{note}</span>
                </div>
              </div>
            ))}
          </div>

          <HomeTemplateShell context={
            <div className="home-band">
              <div className="home-band-intro">
                <p className="uvai-label">Video → tasks → checks</p>
                <h2>Every action has a source.</h2>
                <p>Your source stays the reference. Missing evidence should remain an open question.</p>
              </div>
              <ol className="home-band-steps">
                <li className="home-workflow-step">
                  <span className="home-step-number" aria-hidden="true">01</span>
                  <div><h3>Bring a YouTube URL</h3>
                    <p>A tutorial, product walkthrough, or process recording. Source access and transcript availability affect the result.</p></div>
                </li>
                <li className="home-workflow-step">
                  <span className="home-step-number" aria-hidden="true">02</span>
                  <div><h3>Inspect the Video Pack</h3>
                    <p>Studio organizes the source into a hashed Video Pack. The Tasks view connects requirements to source timestamps and acceptance criteria.</p></div>
                </li>
                <li className="home-workflow-step">
                  <span className="home-step-number" aria-hidden="true">03</span>
                  <div><h3>Inspect the checks</h3>
                    <p>Review each expected output and export the bound tasks. Unrun checks stay unverified; proposed work is not a verified deployment.</p></div>
                </li>
              </ol>
              <ol className="home-agent-flow" aria-label="Agent stand-up flow">
                {AGENT_FLOW.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            </div>
          }>
            <div className="home-bento">
              <article className="home-featured-card">
                <div className="home-featured-top">
                  <p className="uvai-label home-featured-label">
                    <Film size={14} aria-hidden="true" />
                    Universal Video Action Intelligence
                  </p>
                  <Link
                    href="/studio"
                    className="home-tile-badge hover:opacity-90"
                    data-tone="emerald"
                  >
                    NEW · WEBMCP · OPEN STUDIO →
                  </Link>
                </div>
                {showCustomBadge && (
                  <p className="home-flag-badge">New: configurable with Vercel Flags</p>
                )}
                <h1 id="home-heading">Turn YouTube into bound tasks.</h1>
                <p className="home-featured-body">
                  Paste a YouTube URL. UVAI connects source-linked actions, expected outputs,
                  and proposed checks in one workspace. Studio prepares proposed work and build rails for you to review.
                  Follow the timestamp and take the next step toward your build.
                </p>
                <p className="home-featured-note">
                  Transcript quality varies by source. No guaranteed production outcome.
                </p>
                <div className="home-source-composer">
                  <HomePasteForm />
                </div>
              </article>

              <ul className="home-process-tiles" aria-label="UVAI process">
                {PROCESS_TILES.map(({ n, Icon, title, note, chips, badge, tone }) => (
                  <li key={title} className="home-process-tile" data-tone={tone}>
                    <div className="home-tile-head">
                      <span className="home-tile-icon" aria-hidden="true"><Icon size={16} /></span>
                      <div className="home-tile-meta">
                        <span className="home-tile-badge" data-tone={tone}>{badge}</span>
                        <span className="home-tile-index" aria-hidden="true">{n}</span>
                      </div>
                    </div>
                    <h3>{title}</h3>
                    <p>{note}</p>
                    <div className="home-tile-chips">
                      {chips.map((chip) => (
                        <span key={chip}>{chip}</span>
                      ))}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </HomeTemplateShell>

          <section
            id="get-pro"
            aria-labelledby="workflow-pro-heading"
            className="mt-6 flex flex-col gap-5 rounded-xl border px-5 py-5 sm:px-6 lg:flex-row lg:items-center lg:justify-between"
            style={{ borderColor: 'var(--uvai-border-strong)', background: 'var(--uvai-surface)' }}
          >
            <div className="min-w-0 space-y-1.5">
              <p className="uvai-label">Plans &amp; Pro Access</p>
              <h2 id="workflow-pro-heading" className="font-display text-xl sm:text-2xl" style={{ color: 'var(--uvai-ink)' }}>
                Start in Studio, upgrade when you need external dispatch.
              </h2>
              <div className="flex flex-wrap items-center gap-2 pt-1" aria-label="Plan options">
                {OFFERS.map((offer) => (
                  <span
                    key={offer.name}
                    className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs"
                    style={{
                      border: '1px solid var(--uvai-border-strong)',
                      background: 'var(--uvai-surface-warm)',
                      color: 'var(--uvai-ink-soft)',
                    }}
                  >
                    <strong style={{ color: 'var(--uvai-ink)' }}>{offer.name}</strong>
                    <span>{offer.price}</span>
                  </span>
                ))}
              </div>
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-2.5">
              <Link href="/studio" className="uvai-btn uvai-btn-secondary whitespace-nowrap px-4 py-2 text-sm">
                Open Studio
              </Link>
              <Link href="/pricing" className="uvai-btn uvai-btn-primary whitespace-nowrap px-5 py-2 text-sm">
                Get Pro &amp; Compare Plans →
              </Link>
            </div>
          </section>
        </div>
      </section>

      <Footer variant="full" />
    </main>
  );
}
