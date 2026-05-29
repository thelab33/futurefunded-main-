# Before Live Stripe Checklist

## Keep test mode until ready

Before real money:

- Confirm Stripe account is correct.
- Confirm webhook endpoint is live.
- Confirm webhook signing secret is configured.
- Confirm success and cancel URLs.
- Confirm receipt email behavior.
- Confirm test donation appears in dashboard or ledger.
- Confirm live keys are not used during test proof.

## Environment flags for test proof

Use these flags:

    export STRIPE_LIVE_MODE=0
    export FF_PAYMENTS_ENABLED=1
    export FF_EXPECT_TEST_PAYMENTS=1
    export FF_FORBID_LIVE_KEYS=1

## Live switch readiness

Only switch to live mode after:

- Test checkout passes.
- Campaign copy is final.
- Sponsor packages are final.
- Dashboard access is secured.
- Family and sponsor share message is ready.
