'use client';

import Link from 'next/link';
import { useState } from 'react';
import { clsx } from 'clsx';
import Nav from '@/components/Nav';
import Footer from '@/components/Footer';

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
    a: 'Annual billing charges you once per year at a 20% discount compared to monthly billing. For Pro, that&apos;s $15/mo (billed as $180/yr) instead of $19/mo.',
  },
  {
    q: 'What payment methods do you accept?',
    a: 'We accept all major credit cards (Visa, Mastercard, Amex, Discover) and bank transfers for Enterprise. All payments are processed securely via Stripe.',
  },
];

// ─── Components ────────────────────────────────────────────────────────────────

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
      <span className={clsx('mt-0.5 flex-shrink-0 font-bold', color)}>✓</span>
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

      <Nav fixed />

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
          <span className="gradient-text">transparent</span>
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
              background: 'linear-gradient(160deg, rgba(139,92,246,0.12) 0%, rgba(139,92,246,0.04) 60%, rgba(34,211,238,0.04) 100%)',
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

            <Link
              href="/dashboard"
              className="btn btn-primary py-3.5 w-full text-sm text-center shadow-lg shadow-primary-500/30"
            >
              Start 14-day free trial →
            </Link>
            <p className="text-xs text-white/25 text-center mt-3">No credit card required</p>
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
          <div className="text-5xl">🛡️</div>
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
            { label: 'Transcript extraction', free: '✓', pro: '✓', ent: '✓' },
            { label: 'Event extraction', free: '✓', pro: '✓', ent: '✓' },
            { label: 'AI chat messages', free: '5/day', pro: '∞', ent: '∞' },
            { label: 'JSON / CSV export', free: '✓', pro: '✓', ent: '✓' },
            { label: 'Notion + Slack export', free: '—', pro: '✓', ent: '✓' },
            { label: 'REST API access', free: '—', pro: '✓', ent: '✓' },
            { label: 'Agent dispatch', free: '—', pro: '✓', ent: '✓' },
            { label: 'Storage', free: '1 GB', pro: '10 GB', ent: 'Unlimited' },
            { label: 'Priority processing', free: '—', pro: '✓', ent: '✓' },
            { label: 'SSO / SAML', free: '—', pro: '—', ent: '✓' },
            { label: 'Self-hosted deployment', free: '—', pro: '—', ent: '✓' },
            { label: 'Custom MCP integrations', free: '—', pro: '—', ent: '✓' },
            { label: 'SLA guarantee', free: '—', pro: '—', ent: '✓' },
            { label: 'Support', free: 'Community', pro: 'Email', ent: 'Dedicated' },
          ].map((row, i) => (
            <div
              key={row.label}
              className={clsx(
                'grid grid-cols-4 border-b border-white/[0.04] last:border-0',
                i % 2 === 0 ? 'bg-transparent' : 'bg-white/[0.01]'
              )}
            >
              <div className="p-4 text-sm text-white/60">{row.label}</div>
              <div className={clsx('p-4 text-sm text-center', row.free === '—' ? 'text-white/20' : 'text-white/60')}>{row.free}</div>
              <div className={clsx('p-4 text-sm text-center font-medium', row.pro === '—' ? 'text-white/20' : 'text-primary-400')}>{row.pro}</div>
              <div className={clsx('p-4 text-sm text-center font-medium', row.ent === '—' ? 'text-white/20' : 'text-cyan-400')}>{row.ent}</div>
            </div>
          ))}
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
          <div className="text-4xl mb-4">💬</div>
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
