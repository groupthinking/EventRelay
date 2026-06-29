#!/usr/bin/env node
/**
 * Headless browser proof: billing surfaces render with data-testid markers.
 */
import { writeFileSync, mkdirSync, appendFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { chromium } from 'playwright';

const SCRATCH =
  process.env.SCRATCH ||
  '/var/folders/j1/ys2zmm_x4cn7yd156r6vmk780000gn/T/grok-goal-5c43b1f14c7e/implementer';
const BASE = process.env.BASE_URL || 'http://localhost:3000';
const LOG = resolve(SCRATCH, 'app-launch.log');

function log(line) {
  mkdirSync(SCRATCH, { recursive: true });
  appendFileSync(LOG, `${line}\n`);
  console.log(line);
}

mkdirSync(SCRATCH, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext();
const page = await context.newPage();

await page.goto(`${BASE}/pricing`, { waitUntil: 'networkidle' });
await page.waitForSelector('[data-testid="pro-checkout-button"]', { timeout: 15_000 });
await page.waitForSelector('[data-testid="turnstile-widget"]', { timeout: 15_000 });

let pricing = await page.evaluate(() => ({
  checkout: !!document.querySelector('[data-testid="pro-checkout-button"]'),
  turnstile: !!document.querySelector('[data-testid="turnstile-widget"]'),
  renew: !!document.querySelector('[data-testid="pro-renew-panel"]'),
}));

log(`render pricing checkout=${pricing.checkout} turnstile=${pricing.turnstile} renew=${pricing.renew}`);
await page.screenshot({ path: resolve(SCRATCH, 'pricing-billing-ui.png'), fullPage: false });

const billingEmail =
  process.env.BILLING_UI_EMAIL ||
  (process.env.BILLING_UI_COOKIE?.match(/er_billing_email=([^;]+)/)?.[1] ?? 'ui-proof@example.com');

await context.addCookies([
  {
    name: 'er_billing_email',
    value: billingEmail,
    domain: 'localhost',
    path: '/',
    httpOnly: true,
    secure: false,
    sameSite: 'Lax',
  },
]);

await page.goto(`${BASE}/pricing`, { waitUntil: 'networkidle' });
try {
  await page.waitForSelector('[data-testid="pro-renew-panel"]', { timeout: 10_000 });
} catch {
  await page.waitForTimeout(2000);
}
pricing = {
  ...pricing,
  renew: await page.evaluate(
    () => !!document.querySelector('[data-testid="pro-renew-panel"]'),
  ),
};
log(`render pricing renew_with_cookie=${pricing.renew} email=${billingEmail}`);
await page.screenshot({ path: resolve(SCRATCH, 'pricing-renew-ui.png'), fullPage: false });

await page.goto(`${BASE}/dashboard`, { waitUntil: 'networkidle' });
try {
  await page.waitForSelector('[data-testid="billing-status-banner"]', { timeout: 10_000 });
} catch {
  await page.waitForTimeout(2000);
}
const dashboard = await page.evaluate(() => ({
  banner: !!document.querySelector('[data-testid="billing-status-banner"]'),
}));

log(`render dashboard banner=${dashboard.banner}`);
await page.screenshot({ path: resolve(SCRATCH, 'dashboard-billing-ui.png'), fullPage: false });

await browser.close();

const summary = { pricing, dashboard, screenshots: ['pricing-billing-ui.png', 'dashboard-billing-ui.png'] };
writeFileSync(resolve(SCRATCH, 'ui-render-proof.json'), JSON.stringify(summary, null, 2));

if (!pricing.checkout || !pricing.turnstile || !pricing.renew) {
  process.exit(1);
}