# GATE-3 reprobe

- session: `gate3-reprobe-20260714T201739Z`
- git: `64968c272`
- base: `https://uvai.io`

| probe | HTTP | body (trunc) |
|---|---|---|
| activate-empty | 400 | `{"error":"session_id_required"}` |
| auth-csrf | 200 | `{"csrfToken":"98f247abad03627d3d2d91b4ed243f6961b4ef5934fe3b64fe99a80899b3a03b"}` |
| auth-providers | 200 | `{"google":{"id":"google","name":"Google","type":"oauth","signinUrl":"https://uvai.io/api/auth/signin/google","callbackUrl":"https://uvai.io/api/auth/callback/google"}}` |
| auth-session | 200 | `{}` |
| billing-status | 200 | `{"plan":"free","status":"inactive","email":null,"features":{"unlimitedChat":false,"agentDispatch":false,"apiAccess":false,"chatDailyLimit":5},"routing":{"model":"gpt-4o-mini","runt` |
| checkout-empty | 403 | `{"error":"turnstile_token_missing"}` |
| checkout-token | 403 | `{"error":"turnstile_verification_failed"}` |
| renew-empty | 200 | `{"sessionId":"cs_test_a1ZyLqXsqlPHo9BacK21UQdd5vKvp1Pcrwxm2ZgMpqGQjGOz1Ilev1BNm4","url":"https://checkout.stripe.com/c/pay/cs_test_a1ZyLqXsqlPHo9BacK21UQdd5vKvp1Pcrwxm2ZgMpqGQjGOz1` |
| webhook-badsig | 400 | `{"error":"No signatures found matching the expected signature for payload. Are you passing the raw request body you received from Stripe? \n If a webhook request is being forwarded` |
| webhook-empty | 400 | `{"error":"missing_signature"}` |
| webhook-nosig | 400 | `{"error":"missing_signature"}` |

## Renew session (Stripe)

```
session mode=subscription status=open amount_total=1900 prices=['price_1TtCZXPPnkyjEyFR8dYmDo52']
```

## Pass criteria

- **PASS** webhook secret live (no 503): HTTP 400 {"error":"missing_signature"}
- **PASS** webhook rejects missing/bad sig: HTTP 400
- **PASS** renew creates checkout session: HTTP 200
- **PASS** renew not old price_1Tos02: {"sessionId":"cs_test_a1ZyLqXsqlPHo9BacK21UQdd5vKvp1Pcrwxm2ZgMpqGQjGOz1Ilev1BNm4","url":"https://checkout.stripe.com/c/p
- **PASS** checkout empty turnstile gate: HTTP 403 {"error":"turnstile_token_missing"}
- **PASS** auth providers 200: HTTP 200
- **PASS** webhook badsig rejected: HTTP 400 {"error":"No signatures found matching the expected signature for payload. Are y

## Overall: **PASS**

