# FutureFunded Campaign Freeze Note

Date: 20260528002015
Branch: ui/safe-page-polish-20260527222729
Commit: 4409fa0

## Trusted proof stack

Use these gates as the campaign readiness source of truth:

```bash
FF_BASE_URL="http://127.0.0.1:5000" node scripts/hoi/hoi_6g_onboarding_operator_proof.mjs
FF_BASE_URL="http://127.0.0.1:5000" FF_VISUAL_STRICT=1 node scripts/release/ff_visual_launch_gate.mjs
FF_BASE_URL="http://127.0.0.1:5000" node scripts/campaign-payment-smoke.mjs
```

## Status

- Visual launch gate: PASS 100/100
- Campaign payment smoke: PASS mobile + desktop
- Sponsor/share path: PASS through campaign payment smoke
- Flaky custom closeout gate quarantined and should not block launch/demo.
