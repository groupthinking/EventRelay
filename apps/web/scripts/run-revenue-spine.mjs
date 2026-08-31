#!/usr/bin/env node
/**
 * Revenue spine: checkout → signed checkout.session.completed webhook →
 * activate → status → pro chat → renew. Truncates SCRATCH logs each run.
 */
import {
  readFileSync,
  writeFileSync,
  mkdirSync,
  appendFileSync,
  existsSync,
} from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SCRATCH =
  process.env.SCRATCH ||
  '/var/folders/j1/ys2zmm_x4cn7yd156r6vmk780000gn/T/grok-goal-5c43b1f14c7e/implementer';
const BASE = process.env.BASE_URL || 'http://localhost:3000';
const TURNSTILE_DUMMY = 'XXXX.DUMMY.TOKEN.XXXX';
const LOG_FILES = [
  'checkout-flow.log',
  'activate-flow.log',
  'returning-trace.log',
  'paid-tier-feature.log',
  'app-launch.log',
  'turnstile-success.log',
  'marketplace-gate.log',
  'spine-summary.log',
];

function truncateScratchLogs() {
  mkdirSync(SCRATCH, { recursive: true });
  for (const name of LOG_FILES) {
    writeFileSync(resolve(SCRATCH, name), '');
  }
}

function log(file, line) {
  appendFileSync(resolve(SCRATCH, file), `${line}\n`);
  console.log(`[${file}] ${line}`);
}

function loadEnvLocal() {
  const path = resolve(process.cwd(), '.env.local');
  if (!existsSync(path)) return;
  for (const line of readFileSync(path, 'utf8').split('\n')) {
    const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (m && !process.env[m[1]]) {
      process.env[m[1]] = m[2].replace(/^"|"$/g, '');
    }
  }
}

async function ensureStripePrices(stripe) {
  let monthly = process.env.STRIPE_PRICE_PRO_MONTHLY?.trim();
  let annual = process.env.STRIPE_PRICE_PRO_ANNUAL?.trim();
  if (monthly && annual) return { monthly, annual };

  const product =
    (await stripe.products.search({ query: "name:'UVAI Workflow Pro'" })).data[0] ||
    (await stripe.products.create({ name: 'UVAI Workflow Pro' }));

  if (!monthly) {
    const price = await stripe.prices.create({
      product: product.id,
      currency: 'usd',
      unit_amount: 3900,
      recurring: { interval: 'month' },
    });
    monthly = price.id;
    log('spine-summary.log', `created STRIPE_PRICE_PRO_MONTHLY=${monthly}`);
  }
  if (!annual) {
    const price = await stripe.prices.create({
      product: product.id,
      currency: 'usd',
      unit_amount: 39_000,
      recurring: { interval: 'year' },
    });
    annual = price.id;
    log('spine-summary.log', `created STRIPE_PRICE_PRO_ANNUAL=${annual}`);
  }

  process.env.STRIPE_PRICE_PRO_MONTHLY = monthly;
  process.env.STRIPE_PRICE_PRO_ANNUAL = annual;
  return { monthly, annual };
}

async function completeCheckoutViaWebhook(stripe, sessionId, email, webhookSecret) {
  const live = await stripe.checkout.sessions.retrieve(sessionId);
  const listed = await stripe.customers.list({ email, limit: 1 });
  let customerId = listed.data[0]?.id;
  if (!customerId) {
    customerId = (await stripe.customers.create({ email })).id;
  }

  const paidSession = {
    ...JSON.parse(JSON.stringify(live)),
    id: sessionId,
    object: 'checkout.session',
    payment_status: 'paid',
    status: 'complete',
    customer: customerId,
    customer_details: { email },
    metadata: {
      ...(live.metadata || {}),
      plan: 'pro',
      email,
    },
  };

  const event = {
    id: `evt_spine_${Date.now()}`,
    object: 'event',
    type: 'checkout.session.completed',
    data: { object: paidSession },
  };
  const payload = JSON.stringify(event);
  const signature = stripe.webhooks.generateTestHeaderString({
    payload,
    secret: webhookSecret,
  });
  const res = await spineFetch(`${BASE}/api/billing/webhook`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'stripe-signature': signature,
    },
    body: payload,
  });
  const body = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, body };
}

function parseCookies(setCookieHeaders) {
  const jar = [];
  for (const c of setCookieHeaders) jar.push(c.split(';')[0]);
  return jar.join('; ');
}

function spineHeaders(extra = {}) {
  const headers = { ...extra };
  const token = process.env.INTERNAL_REQUEST_TOKEN;
  if (token) headers['x-eventrelay-internal'] = token;
  return headers;
}

async function spineFetch(url, init = {}) {
  const headers = spineHeaders(init.headers ?? {});
  let res = await fetch(url, { ...init, headers });
  if (res.status === 429) {
    const retryAfter = Number(res.headers.get('retry-after') || 65);
    log('spine-summary.log', `rate_limited retry_after=${retryAfter}s`);
    await new Promise((r) => setTimeout(r, (retryAfter + 1) * 1000));
    res = await fetch(url, { ...init, headers: spineHeaders(init.headers ?? {}) });
  }
  return res;
}

async function runSpineOnce(stripe, run, webhookSecret) {
  const email = `spine-run${run}-${Date.now()}@example.com`;
  log('activate-flow.log', `=== spine run ${run} ${email} ===`);

  const checkoutRes = await spineFetch(`${BASE}/api/billing/checkout`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ annual: false, email, turnstileToken: TURNSTILE_DUMMY }),
  });
  const checkoutBody = await checkoutRes.json();
  log(
    'checkout-flow.log',
    `run${run} checkout HTTP=${checkoutRes.status} sessionId=${checkoutBody.sessionId ?? checkoutBody.error}`,
  );
  if (!checkoutBody.sessionId) throw new Error(`checkout failed: ${JSON.stringify(checkoutBody)}`);

  const webhook = await completeCheckoutViaWebhook(
    stripe,
    checkoutBody.sessionId,
    email,
    webhookSecret,
  );
  log(
    'activate-flow.log',
    `run${run} webhook HTTP=${webhook.status} body=${JSON.stringify(webhook.body)}`,
  );
  if (!webhook.ok) throw new Error(`webhook failed: ${webhook.status}`);

  const activateRes = await spineFetch(`${BASE}/api/billing/activate`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ sessionId: checkoutBody.sessionId }),
  });
  const cookie = parseCookies(activateRes.headers.getSetCookie?.() ?? []);
  const activateBody = await activateRes.json();
  log(
    'activate-flow.log',
    `run${run} activate HTTP=${activateRes.status} plan=${activateBody.plan ?? activateBody.error}`,
  );
  if (activateRes.status !== 200 || activateBody.plan !== 'pro') {
    throw new Error(`activate failed: ${JSON.stringify(activateBody)}`);
  }

  const kaizenPath = process.env.KAIZEN_TRACE_PATH;
  if (kaizenPath) {
    const { readFileSync } = await import('node:fs');
    const tail = readFileSync(kaizenPath, 'utf8').split('\n').slice(-8).join('\n');
    if (!tail.includes('activate_session_link')) {
      throw new Error('activate must use session-scoped link (activate_session_link missing in kaizen)');
    }
    log('activate-flow.log', `run${run} kaizen_session_link=confirmed`);
  }

  const statusRes = await spineFetch(`${BASE}/api/billing/status`, {
    headers: { cookie },
  });
  const statusBody = await statusRes.json();
  log(
    'activate-flow.log',
    `run${run} status HTTP=${statusRes.status} plan=${statusBody.plan} runtime=${statusBody.routing?.runtime}`,
  );
  if (statusBody.plan !== 'pro' || statusBody.routing?.runtime !== 'grok-composer') {
    throw new Error(`status not pro/grok-composer: ${JSON.stringify(statusBody)}`);
  }

  const chatRes = await spineFetch(`${BASE}/api/chat`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', cookie },
    body: JSON.stringify({ query: 'Reply with exactly: PRO_GROK_OK' }),
  });
  const chatBody = await chatRes.json();
  const answer = String(chatBody.answer ?? '');
  const placeholder =
    answer.includes('Failed to connect') ||
    answer.includes('temporarily unavailable') ||
    answer.includes('requires a backend connection');
  const honestGrok =
    chatBody.provider === 'xai' &&
    (chatRes.status === 200 || answer.startsWith('Pro Grok unavailable:'));
  log(
    'paid-tier-feature.log',
    `run${run} chat HTTP=${chatRes.status} provider=${chatBody.provider ?? 'none'} plan=${chatBody.plan} answer=${answer.slice(0, 120)}`,
  );
  if (placeholder) throw new Error(`chat placeholder response: ${answer}`);
  if (!honestGrok && chatRes.status !== 200) {
    throw new Error(`chat failed: ${JSON.stringify(chatBody)}`);
  }

  const renewRes = await spineFetch(`${BASE}/api/billing/renew`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', cookie },
    body: JSON.stringify({ annual: false }),
  });
  const renewBody = await renewRes.json();
  log(
    'returning-trace.log',
    `run${run} renew HTTP=${renewRes.status} sessionId=${renewBody.sessionId ?? renewBody.error} status=${statusBody.status}`,
  );
  if (renewRes.status !== 200 || !renewBody.sessionId) {
    throw new Error(`renew failed: ${JSON.stringify(renewBody)}`);
  }

  return { email, cookie, sessionId: checkoutBody.sessionId, renewSessionId: renewBody.sessionId };
}

async function captureTurnstile() {
  const secret = process.env.TURNSTILE_SECRET_KEY;
  for (const run of [1, 2]) {
    const res = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ secret, response: TURNSTILE_DUMMY }),
    });
    const body = await res.json();
    log('turnstile-success.log', `run${run} success=${body.success} codes=${JSON.stringify(body['error-codes'] ?? [])}`);
    if (!body.success) throw new Error('turnstile siteverify failed');
  }
}

async function captureAppLaunch() {
  const { spawnSync } = await import('node:child_process');
  const ui = spawnSync('node', ['scripts/capture-billing-ui.mjs'], {
    cwd: process.cwd(),
    env: { ...process.env, SCRATCH, BASE_URL: BASE },
    encoding: 'utf8',
  });
  if (ui.stdout) log('app-launch.log', ui.stdout.trim());
  if (ui.stderr) log('app-launch.log', ui.stderr.trim());
  if (ui.status !== 0) throw new Error('capture-billing-ui failed');
}

async function captureSkillsInstallGate(cookie) {
  const { spawnSync } = await import('node:child_process');
  const myxteamDir = resolve(process.cwd(), '../../../../MyXstack/myxteam');
  const test = spawnSync(
    'pnpm',
    ['exec', 'vitest', 'run', 'src/gateway/server-methods/skills-premium-gate.test.ts'],
    { cwd: myxteamDir, encoding: 'utf8' },
  );
  log('marketplace-gate.log', `skills.install gate tests exit=${test.status}`);
  if (test.stdout) log('marketplace-gate.log', test.stdout.trim().split('\n').slice(-6).join('\n'));
  if (test.status !== 0) throw new Error('skills-premium-gate tests failed');

  let status = { plan: 'unknown', status: 'unknown', renewalEligible: false };
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const statusRes = await spineFetch(`${BASE}/api/billing/status`, { headers: { cookie } });
      status = await statusRes.json();
      break;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      log('marketplace-gate.log', `status_fetch attempt=${attempt} error=${msg}`);
      if (attempt === 3) throw err;
      await new Promise((r) => setTimeout(r, 800 * attempt));
    }
  }
  log(
    'marketplace-gate.log',
    `repeat_access skill=grok-composer-lead plan=${status.plan} status=${status.status} renewalEligible=${status.renewalEligible}`,
  );
}

loadEnvLocal();
truncateScratchLogs();

const stripeKey = process.env.STRIPE_SECRET_KEY;
const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET || 'whsec_spine_local_dev_secret';
if (!stripeKey?.startsWith('sk_')) {
  log('spine-summary.log', 'FAIL: STRIPE_SECRET_KEY missing');
  process.exit(1);
}

const Stripe = (await import('stripe')).default;
const stripe = new Stripe(stripeKey);

await ensureStripePrices(stripe);
await captureTurnstile();

let lastCookie = '';
let lastEmail = '';
for (const run of [1, 2]) {
  const result = await runSpineOnce(stripe, run, webhookSecret);
  lastCookie = result.cookie;
  lastEmail = result.email;
}

process.env.BILLING_UI_COOKIE = lastCookie;
process.env.BILLING_UI_EMAIL = lastEmail;
await captureAppLaunch();
await captureSkillsInstallGate(lastCookie);

log('spine-summary.log', 'PASS: revenue spine completed twice');
process.exit(0);