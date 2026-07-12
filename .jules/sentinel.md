## 2026-07-12 - Insecure SSL Verification

**Vulnerability:** Man-in-the-Middle (MitM) Attack via disabled SSL certificate verification in `aiohttp`.

**Learning:** Explicitly disabling SSL certificate verification (e.g., `ssl_context.verify_mode = ssl.CERT_NONE` or `ssl_context.check_hostname = False`) disables crucial cryptographic checks that ensure you're communicating with the intended server, leaving API clients vulnerable to MitM attacks.

**Prevention:** Never disable SSL verification in production environments or API clients like `aiohttp`; always rely on secure defaults.
