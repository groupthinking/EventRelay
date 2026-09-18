# Network Configuration

## Purpose
Use this skill to design, validate, and tune network configuration for services, edge environments, and local development stacks.

## When to Use
- Set up hostnames, ports, service discovery, and routing rules
- Review firewall, proxy, ingress, and load-balancing configuration
- Validate environment-specific networking assumptions before deployment
- Diagnose configuration drift between local, staging, and production systems

## Core Guidance
1. Start with the intended topology and required traffic paths.
2. Check identity, reachability, and trust boundaries before changing behavior.
3. Prefer explicit protocols, ports, and names over implicit defaults.
4. Verify that configuration changes are mirrored across all environments.
5. Record the expected network contract so future changes can be validated quickly.

## Typical Checks
- DNS and hostname resolution
- Port exposure and listener configuration
- TLS termination and redirect rules
- Service-to-service routing and upstream dependencies
- Proxy, NAT, and ingress policy correctness

## Safety Rules
- Do not assume a service can reach another without a direct connectivity check.
- Keep network policy changes minimal and reversible.
- Validate security constraints at the same time as connectivity and performance.
- Prefer evidence from live configuration and runtime behavior over static assumptions.
