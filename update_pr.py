import urllib.request
import json
import os

token = os.environ.get('GH_TOKEN')
if not token:
    print('No token')

req = urllib.request.Request('https://api.github.com/repos/groupthinking/EventRelay/pulls/1020', method='PATCH')
req.add_header('Authorization', f'Bearer {token}')
req.add_header('Content-Type', 'application/json')
data = json.dumps({
    'body': '''## Canonical issue
Closes #1020

## Outcome
Refactored `AgentFlowVisualizer.tsx` and `transcription-service.ts` to optimize performance and prevent possible Maximum Call Stack Size Exceeded errors.

## Scope
- Included: apps/web/src/components/AgentFlowVisualizer.tsx, apps/web/src/lib/transcription-service.ts
- Explicitly excluded: Everything else

## Risk
- Risk level: low
- Failure mode: Code crashes on edge cases like extremely large arrays
- Rollback: Revert PR

## Verification
Vitest passes completely and reliably without allocating massive strings or arrays.

- [x] Focused tests
- [x] Required CI
- [x] Review threads resolved

## Production evidence
Not applicable - pure algorithmic optimization, visual behavior unchanged.

## Agent handoff

- [x] One canonical issue is linked
- [x] No competing PR implements the same issue
- [x] Acceptance criteria are satisfied
- [x] Required checks pass on the current head
- [x] Human decision is requested only for product, security, irreversible infrastructure, or production approval

## Agent provenance

<!-- agent-lock-manifest {"issue_number": 1020, "agent_login": "google-labs-jules[bot]", "run_id": "89809620843"} -->
'''
}).encode('utf-8')

try:
    urllib.request.urlopen(req, data=data)
    print("Done")
except Exception as e:
    print(e)
