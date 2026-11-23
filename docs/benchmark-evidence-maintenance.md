# Benchmark evidence maintenance

Static examples in `apps/web/src/lib/verified-benchmarks.ts` are fixtures, not provider receipts. Their hashes verify only the integrity of the checked-in text. Titles, timestamps and source URLs do not verify that text against a video.

When editing these examples, preserve `static-fixture` acquisition/source, `transcriptVerified: false`, an empty acquisition timestamp, null measured latency and a nonpassing, unavailable quality assessment. Never substitute a fixture for a failed live extraction.

Run `npm test --workspace apps/web -- src/lib/__tests__/verified-benchmarks.test.ts src/lib/__tests__/analysis-evidence.test.ts src/lib/__tests__/linked-sop.test.ts` before submitting a change. The regression test must reject fixture acceptance while retaining hash integrity and scaffold generation.

Record real provider acceptance separately with the source URL, immutable code revision, acquisition receipt, observed timestamps, attempts and outcomes. A successful fixture test is not live acceptance. This correction does not resolve the durable workflow acceptance gate tracked in https://github.com/groupthinking/EventRelay/pull/2472.
