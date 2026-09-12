# Network Performance

## Purpose
Use this skill to measure, troubleshoot, and improve network behavior for latency-sensitive and throughput-heavy workloads.

## When to Use
- Response times are slower than expected
- Throughput or transfer rates are below target
- Traffic patterns are spiky or inconsistent under load
- You need to compare baseline and optimized network paths

## Core Approach
1. Measure the current baseline with clear success criteria.
2. Identify the slowest hop, dependency, or resource boundary.
3. Separate protocol overhead from infrastructure bottlenecks.
4. Validate the effect of tuning against the same workload and traffic profile.
5. Keep changes measurable and reversible.

## Typical Optimizations
- Reduce redundant hops and avoid unnecessary retries
- Improve connection reuse and keepalive behavior
- Tune timeouts and backlog handling for realistic load
- Split large payloads or compress where appropriate
- Move expensive traffic closer to the workload or consumer

## Guardrails
- Never optimize blindly without a before-and-after measurement.
- Verify that performance gains do not reduce correctness or resilience.
- Distinguish seasonal or burst-based latency from sustained bottlenecks.
- Keep production changes aligned with the documented service contract.
