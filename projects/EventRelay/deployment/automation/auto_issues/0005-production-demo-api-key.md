Title: Security — Example production API key in `scripts/production_demo.py`

Summary
-------
`scripts/production_demo.py` contains a string `API_KEY = "uvai_prod_10ac559f899665b1cb9dbf075b6966a0"`. Even if this is a demo key, it should not exist in source.

Remediation
---------
1. Remove the key and move to environment variables or GitHub secrets.
2. If it's a real key, rotate it immediately.
3. Add a script to detect and fail CI on API-key-shaped strings.

Suggested labels: security, infra
