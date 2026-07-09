# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: production.spec.ts >> EventRelay Production E2E >> features page shows workflow templates
- Location: tests/e2e/production.spec.ts:21:7

# Error details

```
Error: expect(received).toContain(expected) // indexOf

Expected substring: "workflow"
Received string:    "{\"error\":\"rate limit exceeded. please try again shortly.\"}"
```

# Page snapshot

```yaml
- generic [ref=e2]: "{\"error\":\"Rate limit exceeded. Please try again shortly.\"}"
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  |
  3  | const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
  4  |
  5  | test.describe('EventRelay Production E2E', () => {
  6  |   test('homepage loads and shows welcome message', async ({ page }) => {
  7  |     await page.goto(BASE_URL);
  8  |     // Homepage is the Video Workflow Studio, it should have a YouTube URL input or similar indicators
  9  |     const content = await page.textContent('body');
  10 |     expect(content).toContain('UVAI');
  11 |   });
  12 |
  13 |   test('dashboard page renders', async ({ page }) => {
  14 |     await page.goto(`${BASE_URL}/dashboard`);
  15 |     const h1 = await page.locator('h1');
  16 |     const text = await h1.first().textContent();
  17 |     // Allow for various titles like 'Dashboard', 'Analytics', etc.
  18 |     expect(text?.length).toBeGreaterThan(0);
  19 |   });
  20 |
  21 |   test('features page shows workflow templates', async ({ page }) => {
  22 |     await page.goto(`${BASE_URL}/features`);
  23 |     const content = await page.textContent('body');
> 24 |     expect(content?.toLowerCase()).toContain('workflow');
     |                                    ^ Error: expect(received).toContain(expected) // indexOf
  25 |   });
  26 | });
  27 |
```