# ZarinPal Sandbox Verification Procedure

Verified facts (2026-10-13, live HTTPS from this host):

- `POST .../pg/v4/payment/request.json` **accepts any merchant id** in the
  sandbox and returns a real `authority` + StartPay URL. Covered by
  `TestLiveSandboxConnectivity::test_sandbox_issues_authority_for_any_merchant`
  (run with `RUN_LIVE_SANDBOX_TESTS=1`).
- `POST .../pg/v4/payment/verify.json` with a non-merchant id returns
  **HTTP 401** → the adapter reports a transport-class failure and the
  service leaves the payment `PENDING` (retryable, never credited).
  Covered by `test_sandbox_verify_rejects_unpaid_authority` and
  `test_service_callback_with_real_gateway_fails_unpaid`.
- Positive verification (codes 100/101) strictly requires a **real sandbox
  merchant id**. No credentials exist in this environment
  (`ZARINPAL_MERCHANT_ID` is empty in production config).

## Positive-flow verification (needs a real sandbox merchant id)

Prerequisites (owner action):

1. Register at ZarinPal and enable the **sandbox** merchant account.
2. Copy the sandbox merchant id. Do NOT commit it anywhere.

Execution (all on a disposable database; amounts are sandbox-only):

```bash
export ZARINPAL_SANDBOX_MERCHANT_ID="<paste-id-here>"   # shell only, never a file
export RUN_LIVE_SANDBOX_TESTS=1
python -m pytest tests/test_payment.py::TestLiveSandboxConnectivity -q
```

Then complete a payment in a real browser:

1. `POST /finance/student/pay` (logged in as a seeded student) with a small
   amount (e.g. 1000 Toman) → redirected to `sandbox.zarinpal.com/pg/StartPay/…`.
2. Pay with the sandbox test card shown on the gateway page.
3. ZarinPal redirects to `/finance/payment/callback?Authority=…&Status=OK`.
4. Assert: transaction row is `ACTIVE` with `gateway_ref_id` set, student
   balance increased exactly once, receipt page shows the payment.
5. Repeat the callback URL (duplicate delivery) → still exactly one credit.
6. Start a second payment and abandon it on the gateway page → after the
   `Status=NOK` redirect the row must stay `PENDING` (or become `FAILED`
   only on definitive provider rejection), balance unchanged.
7. Expire/scrub: the sandbox merchant id stays in shell history — clear it
   (`history -d`, new shell) and never store it in the repo, `.env` files
   committed to Git, logs, or screenshots.

## What remains unverified without the above

Provider success codes 100/101 handling, `ref_id`/`card_pan` parsing, and
any sandbox-specific quirks (e.g. verify-after-cancel semantics) are
mock-tested only. Payment activation must stay blocked until this
procedure is executed with a real merchant id.
