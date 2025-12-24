Title: Build blocker — fix invalid `fsspec` version in `requirements.txt`

Summary
-------
The repository `requirements.txt` pins `fsspec==2027.0`, which does not exist and prevents `pip install -r requirements.txt` from completing. This blocks backend dependency installation and CI.

Evidence
--------
- `requirements.txt` contains `fsspec==2027.0` (future version). The environment used for development expects `fsspec==2024.9.0` or similar.

Impact
------
- Developers and CI can't install Python dependencies reliably.
- Docker builds and production packaging may fail.

Recommended remediation
----------------------
1. Replace `fsspec==2027.0` with a valid version such as `fsspec==2024.9.0` or `fsspec>=2024.9.0,<2025.0.0`.
2. Run `python3 -m pip install -r requirements.txt` in CI to confirm the change.
3. Consider pinning other problematic future versions and running a dependency audit.

Next steps (automated)
----------------------
- Open a small PR that updates `requirements.txt` and runs the `python3 build.py --api-only` check.

Suggested labels: bug, infra, CI
