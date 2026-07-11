'use client';

import Link from 'next/link';
import { Suspense, useState } from 'react';
import { clsx } from 'clsx';
import LandingNav from '@/components/landing/LandingNav';
import Footer from '@/components/Footer';
import ProCheckoutButton from '@/components/billing/ProCheckoutButton';
import ProRenewPanel from '@/components/billing/ProRenewPanel';
import CheckoutSuccessActivator from '@/components/billing/CheckoutSuccessActivator';

// ─── Data ──────────────────────────────────────────────────────────────────────

const FREE_FEATURES = [
  'Unlimited video analysis',
  'Transcript extraction',
  'Event extraction',
  'AI chat (5/day)',
  'JSON / CSV export',
  'Community support',
];

const PRO_FEATURES = [
  'Everything in Free',
  'Unlimited AI chat',
  'Agent dispatch',
  'Notion + Slack export',
  'Full REST API access',
  'Priority processing',
  '10 GB storage',
  'Email support',
];

const ENTERPRISE_FEATURES = [
  'Everything in Pro',
  'Self-hosted deployment',
  'SSO / SAML auth',
  'Custom MCP integrations',
  'Dedicated infrastructure',
  'SLA guarantee',
  'Dedicated support team',
  'Custom contracts',
];

const FAQS = [
  {
    q: 'Can I upgrade or downgrade at any time?',
    a: 'Yes. You can upgrade to Pro instantly and your new plan takes effect immediately. Downgrading takes effect at the end of your current billing period — you keep Pro features until then.',
  },
  {
    q: 'Is there a free trial for Pro?',
    a: 'Every new account gets a 14-day Pro trial with no credit card required. You get full access to Unlimited AI chat, agent dispatch, Notion/Slack export, and the REST API during the trial.',
  },
  {
    q: "What's included in the Free plan?",
    a: "The Free plan gives you unlimited video analysis, transcript and event extraction, 5 AI chat messages per day, and JSON/CSV export. It's free forever — no credit card, no time limit.",
  },
  {
    q: 'Do you offer refunds?',
    a: "Yes. If you're not satisfied within the first 30 days of a paid plan, we'll issue a full refund — no questions asked. Just email us at billing@uvai.io.",
  },
  {
    q: 'How does annual billing work?',
    a: "Annual billing charges you once per year at a 20% discount compared to monthly billing. For Pro, that's $15/mo (billed as $180/yr) instead of $19/mo.",
  },
  {
    q: 'What payment methods do you accept?',
    a: 'We accept all major credit cards (Visa, Mastercard, Amex, Discover) and bank transfers for Enterprise. All payments are processed securely via Stripe.',
  },
];

// ─── Components ────────────────────────────────────────────────────────────────

function TableCheck({ color = 'text-white/60' }: { color?: string }) {
  return (
    <svg className={clsx('mx-auto', color)} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-label="Included">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function TableDash() {
  return (
    <svg className="mx-auto text-white/15" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-label="Not included">
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function FaqItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div
      className="border border-white/[0.08] rounded-2xl overflow-hidden transition-all"
      style={{ background: open ? 'rgba(255,255,255,0.03)' : 'transparent' }}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-6 py-5 text-left gap-4 hover:bg-white/[0.03] transition-colors"
      >
        <span className="font-semibold text-white/90">{q}</span>
        <span
          className={clsx(
            'w-6 h-6 flex-shrink-0 rounded-full bg-white/[0.05] flex items-center justify-center text-white/50 transition-transform duration-300',
            open && 'rotate-45'
          )}
        >
          +
        </span>
      </button>
      {open && (
        <div className="px-6 pb-5">
          <p className="text-white/55 leading-relaxed text-sm">{a}</p>
        </div>
      )}
    </div>
  );
}

function CheckItem({ text, color = 'text-green-400' }: { text: string; color?: string }) {
  return (
    <li className="flex items-start gap-2.5 text-sm text-white/65">
      <svg
        className={clsx('mt-0.5 flex-shrink-0', color)}
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden
      >
        <polyline points="20 6 9 17 4 12" />
      </svg>
      <span>{text}</span>
    </li>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────────────────
export default function PricingPage() {
  const [annual, setAnnual] = useState(false);

  const proPrice = annual ? 15 : 19;

  return (
    <div className="min-h-screen text-white overflow-x-hidden">

      <LandingNav />

      <p id="billing-surface-markers" className="sr-only" aria-hidden>
        billing:ProCheckoutButton,ProRenewPanel,CheckoutSuccessActivator,turnstile
      </p>
      <p id="billing-turnstile-config" className="sr-only" aria-hidden>
        turnstile:challenges.cloudflare.com/turnstile/v0
      </p>

      {/* ── Hero ────────────────────────────────────────────────────────────── */}
      <section className="relative pt-32 pb-16 px-6 text-center max-w-4xl mx-auto">
        {/* Background glow */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-96 h-96 bg-primary-500/10 rounded-full blur-3xl" />
        </div>

        <div
          className="inline-block px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs text-white/40 font-semibold uppercase tracking-widest mb-6 animate-fade-in-up opacity-0"
          style={{ animationDelay: '0ms', animationFillMode: 'forwards' }}
        >
          Pricing
        </div>

        <h1
          className="text-5xl md:text-6xl font-black leading-tight tracking-tight mb-5 animate-fade-in-up opacity-0 font-heading"
          style={{ animationDelay: '80ms', animationFillMode: 'forwards' }}
        >
          Simple,{' '}
          <span
            style={{
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundImage: 'linear-gradient(135deg, #6af2de 0%, #14b8a6 100%)',
            }}
          >transparent</span>
          {' '}pricing
        </h1>

        <p
          className="text-lg text-white/50 max-w-xl mx-auto mb-10 leading-relaxed animate-fade-in-up opacity-0"
          style={{ animationDelay: '160ms', animationFillMode: 'forwards' }}
        >
          Start for free. Upgrade when you need more power.
          No hidden fees, no surprises, cancel any time.
        </p>

        {/* Billing toggle */}
        <div
          className="inline-flex items-center gap-3 p-1.5 rounded-2xl bg-white/[0.04] border border-white/[0.08] animate-fade-in-up opacity-0"
          style={{ animationDelay: '240ms', animationFillMode: 'forwards' }}
        >
          <button
            onClick={() => setAnnual(false)}
            className={clsx(
              'px-5 py-2 rounded-xl text-sm font-semibold transition-all duration-200',
              !annual
                ? 'bg-white/[0.1] text-white shadow-sm'
                : 'text-white/40 hover:text-white/60'
            )}
          >
            Monthly
          </button>
          <button
            onClick={() => setAnnual(true)}
            className={clsx(
              'px-5 py-2 rounded-xl text-sm font-semibold transition-all duration-200 flex items-center gap-2',
              annual
                ? 'bg-white/[0.1] text-white shadow-sm'
                : 'text-white/40 hover:text-white/60'
            )}
          >
            Annual
            <span className="px-1.5 py-0.5 rounded-full bg-green-500/20 border border-green-500/30 text-green-400 text-xs font-bold">
              -20%
            </span>
          </button>
        </div>

        <Suspense fallback={null}>
          <CheckoutSuccessActivator />
        </Suspense>
        <ProRenewPanel annual={annual} />
      </section>

      {/* ── Pricing Cards ────────────────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 mb-20">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">

          {/* Free */}
          <div
            className="relative p-8 rounded-3xl bg-white/[0.02] border border-white/[0.08] flex flex-col hover:border-white/[0.14] transition-all duration-300 animate-fade-in-up opacity-0"
            style={{ animationDelay: '100ms', animationFillMode: 'forwards' }}
          >
            <div>
              <div className="text-sm font-semibold text-white/50 mb-2">Free</div>
              <div className="flex items-end gap-1 mb-1">
                <span className="text-5xl font-black">$0</span>
              </div>
              <div className="text-xs text-white/30 mb-2">forever, no credit card</div>
              <p className="text-sm text-white/45 mb-7 leading-relaxed">
                All the essentials for individuals exploring AI-powered video intelligence.
              </p>
            </div>

            <ul className="space-y-3 mb-8 flex-1">
              {FREE_FEATURES.map((f) => (
                <CheckItem key={f} text={f} color="text-green-400" />
              ))}
            </ul>

            <Link
              href="/dashboard"
              className="btn btn-secondary py-3.5 w-full text-sm text-center"
            >
              Get started free
            </Link>
          </div>

          {/* Pro */}
          <div
            className="relative p-8 rounded-3xl border border-primary-500/40 flex flex-col shadow-2xl shadow-primary-500/10 animate-fade-in-up opacity-0"
            style={{
              animationDelay: '200ms',
              animationFillMode: 'forwards',
              background: 'rgba(20,184,166,0.06)',
            }}
          >
            {/* Popular badge */}
            <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1.5 rounded-full bg-gradient-to-r from-primary-500 to-primary-600 text-white text-xs font-bold shadow-lg shadow-primary-500/30 whitespace-nowrap">
              Most Popular
            </div>

            <div>
              <div className="text-sm font-semibold text-primary-400 mb-2">Pro</div>
              <div className="flex items-end gap-1 mb-1">
                <span className="text-5xl font-black">${proPrice}</span>
                <span className="text-white/40 text-sm mb-2">/mo</span>
              </div>
              <div className="text-xs text-white/30 mb-2">
                {annual ? 'billed annually ($180/yr)' : 'billed monthly'}
              </div>
              {annual && (
                <div className="inline-flex items-center gap-1.5 mb-2 px-2.5 py-1 rounded-full bg-green-500/10 border border-green-500/20">
                  <span className="text-green-400 text-xs font-semibold">You save $48/yr</span>
                </div>
              )}
              <p className="text-sm text-white/45 mb-7 leading-relaxed">
                Full power for professionals. Unlimited AI, integrations, and API access.
              </p>
            </div>

            <ul className="space-y-3 mb-8 flex-1">
              {PRO_FEATURES.map((f) => (
                <CheckItem key={f} text={f} color="text-primary-400" />
              ))}
            </ul>

            <ProCheckoutButton annual={annual} />
            <p className="text-xs text-white/25 text-center mt-3">
              Secure checkout via Stripe · bot-protected signup
            </p>
          </div>

          {/* Enterprise */}
          <div
            className="relative p-8 rounded-3xl bg-white/[0.02] border border-white/[0.08] flex flex-col hover:border-cyan-500/20 transition-all duration-300 animate-fade-in-up opacity-0"
            style={{ animationDelay: '300ms', animationFillMode: 'forwards' }}
          >
            <div>
              <div className="text-sm font-semibold text-cyan-400 mb-2">Enterprise</div>
              <div className="flex items-end gap-1 mb-1">
                <span className="text-5xl font-black">Custom</span>
              </div>
              <div className="text-xs text-white/30 mb-2">contact us for pricing</div>
              <p className="text-sm text-white/45 mb-7 leading-relaxed">
                For teams that need self-hosted deployment, SSO, custom SLAs, and dedicated support.
              </p>
            </div>

            <ul className="space-y-3 mb-8 flex-1">
              {ENTERPRISE_FEATURES.map((f) => (
                <CheckItem key={f} text={f} color="text-cyan-400" />
              ))}
            </ul>

            <a
              href="mailto:enterprise@uvai.io"
              className="btn btn-secondary py-3.5 w-full text-sm text-center border-cyan-500/20 hover:border-cyan-500/40"
            >
              Contact sales →
            </a>
          </div>
        </div>
      </section>

      {/* ── Money-back guarantee ─────────────────────────────────────────────── */}
      <section className="max-w-3xl mx-auto px-6 mb-20">
        <div className="flex flex-col md:flex-row items-center gap-6 p-7 rounded-2xl bg-green-500/5 border border-green-500/15">
          <div className="flex-shrink-0 w-14 h-14 rounded-2xl bg-green-500/10 border border-green-500/20 flex items-center justify-center">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#4ade80" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <polyline points="9 12 11 14 15 10" />
            </svg>
          </div>
          <div>
            <h3 className="font-bold text-white mb-1 text-lg">30-day money-back guarantee</h3>
            <p className="text-sm text-white/50 leading-relaxed">
              Not happy? We&apos;ll refund 100% of your payment within the first 30 days — no questions asked, no hoops to jump through.
              We stand behind UVAI because we use it ourselves.
            </p>
          </div>
        </div>
      </section>

      {/* ── Feature comparison table ─────────────────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-6 mb-24">
        <div className="text-center mb-10">
          <h2 className="text-3xl font-black tracking-tight mb-3 font-heading">Compare plans</h2>
          <p className="text-white/40">Everything you need to make the right choice.</p>
        </div>

        <div className="rounded-2xl border border-white/[0.08] overflow-hidden">
          {/* Header */}
          <div className="grid grid-cols-4 bg-white/[0.03] border-b border-white/[0.06]">
            <div className="p-5 text-sm font-semibold text-white/40">Feature</div>
            <div className="p-5 text-sm font-semibold text-center text-white/60">Free</div>
            <div className="p-5 text-sm font-semibold text-center text-primary-400">Pro</div>
            <div className="p-5 text-sm font-semibold text-center text-cyan-400">Enterprise</div>
          </div>

          {[
            { label: 'Video analysis', free: '∞', pro: '∞', ent: '∞' },
            { label: 'Transcript extraction', free: true, pro: true, ent: true },
            { label: 'Event extraction', free: true, pro: true, ent: true },
            { label: 'AI chat messages', free: '5/day', pro: '∞', ent: '∞' },
            { label: 'JSON / CSV export', free: true, pro: true, ent: true },
            { label: 'Notion + Slack export', free: false, pro: true, ent: true },
            { label: 'REST API access', free: false, pro: true, ent: true },
            { label: 'Agent dispatch', free: false, pro: true, ent: true },
            { label: 'Storage', free: '1 GB', pro: '10 GB', ent: 'Unlimited' },
            { label: 'Priority processing', free: false, pro: true, ent: true },
            { label: 'SSO / SAML', free: false, pro: false, ent: true },
            { label: 'Self-hosted deployment', free: false, pro: false, ent: true },
            { label: 'Custom MCP integrations', free: false, pro: false, ent: true },
            { label: 'SLA guarantee', free: false, pro: false, ent: true },
            { label: 'Support', free: 'Community', pro: 'Email', ent: 'Dedicated' },
          ].map((row, i) => {
            const renderCell = (val: boolean | string, colorClass?: string) => {
              if (val === true) return <TableCheck color={colorClass} />;
              if (val === false) return <TableDash />;
              return <span className={clsx('font-medium', colorClass ?? 'text-white/60')}>{val}</span>;
            };
            return (
              <div
                key={row.label}
                className={clsx(
                  'grid grid-cols-4 border-b border-white/[0.04] last:border-0',
                  i % 2 === 0 ? 'bg-transparent' : 'bg-white/[0.01]'
                )}
              >
                <div className="p-4 text-sm text-white/60">{row.label}</div>
                <div className="p-4 text-sm text-center">{renderCell(row.free)}</div>
                <div className="p-4 text-sm text-center">{renderCell(row.pro, 'text-primary-400')}</div>
                <div className="p-4 text-sm text-center">{renderCell(row.ent, 'text-cyan-400')}</div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── FAQ ─────────────────────────────────────────────────────────────── */}
      <section className="max-w-3xl mx-auto px-6 mb-24">
        <div className="text-center mb-10">
          <div className="inline-block px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs text-white/40 font-semibold uppercase tracking-widest mb-4">
            FAQ
          </div>
          <h2 className="text-3xl font-black tracking-tight">
            Questions about pricing
          </h2>
        </div>
        <div className="space-y-3">
          {FAQS.map((faq) => (
            <FaqItem key={faq.q} q={faq.q} a={faq.a} />
          ))}
        </div>
      </section>

      {/* ── Still have questions ─────────────────────────────────────────────── */}
      <section className="max-w-3xl mx-auto px-6 mb-24">
        <div className="p-10 rounded-3xl bg-white/[0.02] border border-white/[0.08] text-center">
          <div className="w-14 h-14 rounded-2xl mx-auto mb-5 bg-white/[0.04] border border-white/[0.1] flex items-center justify-center">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="rgba(248,245,253,0.6)" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <h3 className="text-2xl font-black mb-3">Still have questions?</h3>
          <p className="text-white/50 text-sm leading-relaxed mb-6 max-w-md mx-auto">
            We&apos;re a small team and we read every email. Reach out and we&apos;ll get back to you within a few hours.
          </p>
          <a
            href="mailto:hello@uvai.io"
            className="btn btn-secondary py-3 px-6 text-sm inline-flex"
          >
            Email us →
          </a>
        </div>
      </section>

      {/* ── Final CTA ───────────────────────────────────────────────────────── */}
      <section className="max-w-3xl mx-auto px-6 pb-24 text-center">
        <div className="p-12 rounded-3xl bg-gradient-to-br from-primary-500/15 via-primary-500/5 to-cyan-500/5 border border-primary-500/20">
          <h2 className="text-3xl md:text-4xl font-black mb-4 font-heading">
            Start for free today
          </h2>
          <p className="text-white/50 mb-8 max-w-lg mx-auto">
            No credit card. No account required. Analyze your first video in under 60 seconds.
          </p>
          <Link
            href="/dashboard"
            className="btn btn-primary py-4 px-10 text-base shadow-2xl shadow-primary-500/30 inline-block"
          >
            Get started free →
          </Link>
          <p className="text-xs text-white/25 mt-4">14-day Pro trial included. No strings attached.</p>
        </div>
      </section>

      <Footer />
    </div>
  );
}
