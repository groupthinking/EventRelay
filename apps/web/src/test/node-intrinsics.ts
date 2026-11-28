/**
 * @workflow/core 5.x captures host (WHATWG) intrinsics when it is imported —
 * e.g. `Object.getOwnPropertyDescriptor(URL.prototype, 'href').get` in
 * `serialization/hardened.js` — and throws "Missing intrinsic getter: href" if
 * one is absent. Under vitest's jsdom environment the global `URL` is jsdom's
 * wrapper, whose accessors don't live on `URL.prototype`, so any jsdom component
 * test that transitively imports `workflow/api` (e.g. via `@/lib/video-pack`)
 * failed at import time.
 *
 * `workflow` only ever runs in the Node host in production, so restore Node's
 * native WHATWG URL classes before test modules load. This is a no-op under the
 * default `node` environment and leaves every other jsdom global untouched.
 */
import { URL as NodeURL, URLSearchParams as NodeURLSearchParams } from 'node:url';

globalThis.URL = NodeURL as unknown as typeof globalThis.URL;
globalThis.URLSearchParams = NodeURLSearchParams as unknown as typeof globalThis.URLSearchParams;
