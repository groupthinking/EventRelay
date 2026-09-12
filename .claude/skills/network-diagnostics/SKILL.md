# Network Diagnostics

## Purpose
Use this skill to find the root cause of connectivity issues across applications, services, and infrastructure.

## When to Use
- A service is unreachable, slow, or intermittently failing
- DNS, routing, or packet loss needs to be investigated
- Connection attempts fail between related systems or cloud resources
- You need a structured troubleshooting flow for network issues

## Investigation Flow
1. Confirm the symptom and reproduction details.
2. Check whether the issue is local, regional, or cross-service.
3. Validate endpoint reachability, response timing, and protocol correctness.
4. Compare expected and actual routing, DNS, and port behavior.
5. Narrow the fault to a specific layer before making a configuration change.

## Focus Areas
- DNS resolution and certificate validity
- TCP/UDP connectivity and port accessibility
- HTTP status, timeouts, and retry behavior
- Routing loops, asymmetry, or upstream instability
- Intermittent packet loss or elevated latency

## Decision Rules
- Treat an issue as network-related only after confirming the endpoint and path are correct.
- Collect evidence from logs, traceroute or equivalent paths, and service telemetry.
- Keep the investigation focused on the smallest failing scope to avoid broad churn.
- Test the fix under the same conditions that originally reproduced the issue.
