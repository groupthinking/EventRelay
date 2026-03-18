# Ray Serve ML Deployment — Quick Reference

> **Last verified:** 2026-03-18 — 6/6 endpoints passing, 18h uptime, zero restarts.

## What's Running

| Component | Image | Status |
|-----------|-------|--------|
| Head node | `us-central1-docker.pkg.dev/uvai-730bb/uvai-registry/ray-serve-uvai:latest` | ✅ |
| Worker node | same | ✅ |

**Cluster:** `gke_uvai-730bb_us-central1_uvai-cluster-1`
**Namespace:** `gke-ray-system`
**Ray version:** 2.9.0, Python 3.9.18

## Endpoints (port 8000 on head pod)

| Method | Path | What it does |
|--------|------|-------------|
| GET | `/health` | Health check + uptime |
| GET | `/models` | Model metadata + version |
| POST | `/score-transcript` | Predict transcript quality → `{metadata: {...}}` |
| POST | `/score-transcript/outcome` | Record actual result for learning |
| POST | `/rank-actions` | Rank actions by priority → `{actions: [...]}` |
| POST | `/rank-actions/feedback` | Record user feedback for learning |

## Common Commands

```bash
# Check status
kubectl get pods -n gke-ray-system
HEAD=$(kubectl get pods -n gke-ray-system -l ray.io/node-type=head -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n gke-ray-system $HEAD -c ray-head -- serve status

# Quick health check
kubectl exec -n gke-ray-system $HEAD -c ray-head -- python -c "
import urllib.request, json
print(json.dumps(json.loads(urllib.request.urlopen('http://localhost:8000/health').read()), indent=2))
"

# Deploy Ray Serve (after pod restart or config change)
kubectl exec -n gke-ray-system $HEAD -c ray-head -- serve deploy /home/ray/ray-serve-config.yaml

# Shutdown Ray Serve
kubectl exec -n gke-ray-system $HEAD -c ray-head -- serve shutdown -y
```

## Rebuild & Redeploy (after code changes)

The ML models are **baked into the Docker image** — no `kubectl cp` needed.

```bash
# 1. Stage a minimal build context (56KB, not the whole repo)
mkdir -p /tmp/ray-build/src/uvai/ml/models /tmp/ray-build/infrastructure/k8s/ray
cp infrastructure/k8s/ray/Dockerfile.ray /tmp/ray-build/Dockerfile
cp src/uvai/ml/__init__.py src/uvai/ml/serve.py /tmp/ray-build/src/uvai/ml/
cp src/uvai/ml/models/*.py /tmp/ray-build/src/uvai/ml/models/
cp infrastructure/k8s/ray/ray-serve-config.yaml /tmp/ray-build/infrastructure/k8s/ray/

# 2. Build + push via Cloud Build (~3 min, no local Docker needed)
gcloud builds submit /tmp/ray-build \
  --tag us-central1-docker.pkg.dev/uvai-730bb/uvai-registry/ray-serve-uvai:latest \
  --project uvai-730bb

# 3. Roll pods to pick up the new image
kubectl delete pods -n gke-ray-system -l ray.io/cluster=uvai-ray-cluster

# 4. Wait for pods to come back, then deploy serve
sleep 60
HEAD=$(kubectl get pods -n gke-ray-system -l ray.io/node-type=head -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n gke-ray-system $HEAD -c ray-head -- serve deploy /home/ray/ray-serve-config.yaml

# 5. Cleanup
rm -rf /tmp/ray-build
```

## Files in this directory

| File | Purpose |
|------|---------|
| `Dockerfile.ray` | Custom Ray image with UVAI models baked in |
| `ray-serve-config.yaml` | Ray Serve deployment config (autoscaling, routes) |
| `cloudbuild.yaml` | Google Cloud Build config |
| `raycluster-image-patch.yaml` | K8s patch to swap the RayCluster image |

## Gotchas

1. **GCR doesn't work** — use Artifact Registry (`us-central1-docker.pkg.dev/...`), not `gcr.io/...`
2. **Request objects can't cross Ray actors** — the router extracts JSON bodies and passes plain dicts to models via `.remote()` (Starlette `Request` causes uvloop pickle errors)
3. **Code must be on ALL nodes** — if using `kubectl cp`, copy to head AND worker. The baked image solves this automatically.
4. **`serve deploy` caches old code** — after updating files, always `serve shutdown -y` before redeploying, or roll the pods.
5. **`num_replicas` + `autoscaling_config` are mutually exclusive** in Ray 2.9.0
