# Network Security

## Purpose
Use this skill to review network exposure, access boundaries, and secure communication patterns for running systems.

## When to Use
- Hardening network access for apps, APIs, or internal services
- Reviewing trust boundaries between environments or segments
- Verifying TLS, authentication, and least-privilege network exposure
- Assessing the security consequences of routing, proxies, or firewalls

## Core Principles
1. Restrict access to the minimum required surface area.
2. Validate identity and trust before granting any network path.
3. Prefer encrypted, authenticated channels for every cross-service hop.
4. Treat configuration drift as a security risk if it changes boundaries or exposure.
5. Ensure recovery and auditability for every policy change.

## Typical Reviews
- Firewall, ACL, and ingress policy correctness
- TLS certificate health and protocol compliance
- Enforced service-to-service authentication and segmentation
- Reverse-proxy, WAF, and gateway rule safety
- Logging and alerting for suspicious network activity

## Safety Rules
- Prefer fail-closed rules over permissive defaults.
- Check both configuration and runtime behavior before approving a network change.
- Document who can reach what, how, and under which conditions.
- Re-test after any rule or routing update to confirm no unintended exposure was introduced.
