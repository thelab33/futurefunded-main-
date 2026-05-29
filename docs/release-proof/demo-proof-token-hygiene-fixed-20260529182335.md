# Demo Proof Token Hygiene Fixed

Date: 2026-05-29T18:24:20-05:00

Commit under patch:
f8d3802 (HEAD -> main, tag: safety-before-demo-proof-token-hygiene-20260529182020, tag: payment-demo-handoff-proof-20260529181736) Document payment demo handoff proof

Patch:
- scripts/demo/_ff-proof-lib.sh
- scripts/demo/ff-fast-proof.sh
- scripts/demo/ff-full-proof.sh
- scripts/demo/ff-fast-proof-strict.sh
- scripts/release/ff_visual_launch_gate.mjs

Markers:
- hoi-demo-proof-token-preserve-v1
- hoi-demo-proof-token-hygiene-v2
- hoi-demo-proof-strict-fast-wrapper-v1
- hoi-visual-gate-token-fallback-v1

Result:
- Demo proof scripts now preserve exported FF_OPERATOR_ACCESS_TOKEN.
- Visual launch gate reads FF_OPERATOR_ACCESS_TOKEN, OPERATOR_ACCESS_TOKEN, or OPERATOR_TOKEN.
- Local visual gate falls back to the dev operator token only for localhost/127.0.0.1.
- Strict fast proof passes without hidden dashboard-token 403 failures.

Reports:
- audit_outputs/demo-proof-token-hygiene-fixed/20260529182335/reports/route-sanity.txt
- audit_outputs/demo-proof-token-hygiene-fixed/20260529182335/reports/ff-fast-proof-strict.log
- audit_outputs/demo-proof-token-hygiene-fixed/20260529182335/reports/visual-launch-gate-report.md
