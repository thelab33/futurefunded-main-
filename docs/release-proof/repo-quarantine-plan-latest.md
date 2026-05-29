# FutureFunded Repo Quarantine Plan

Generated: `2026-05-20T19:45:57.740645+00:00`

Branch: `production/premium-campaign-rebuild`  
HEAD: `c95dfa8`

## Working tree

```text
M docs/release-proof/repo-quarantine-plan-latest.json
 M docs/release-proof/repo-quarantine-plan-latest.md
 M scripts/final_release_gate.py
 M scripts/qa_campaign_gate.sh
?? repo-quarantine/scripts/legacy-audits/README.md
```

## Summary

- `total_candidates`: `36`
- `tracked_candidates`: `30`
- `untracked_candidates`: `6`

## Candidates

| Risk | Tracked | Size | File | Reasons |
|---|---:|---:|---|---|
| `already-quarantined` | `True` | `779` | `apps/web/app/static/css/_quarantine/wave2e-20260511-185014/MANIFEST.json` | already-quarantined, backup-or-legacy-name |
| `already-quarantined` | `True` | `12889` | `apps/web/app/static/css/_quarantine/wave2e-20260511-185014/ff.base.css` | already-quarantined, backup-or-legacy-name |
| `already-quarantined` | `True` | `151104` | `apps/web/app/static/css/_quarantine/wave2e-20260511-185014/ff.campaign-polish.css` | already-quarantined, backup-or-legacy-name |
| `already-quarantined` | `True` | `30181` | `apps/web/app/static/css/_quarantine/wave2e-20260511-185014/ff.homepage-flagship.css` | already-quarantined, backup-or-legacy-name |
| `already-quarantined` | `True` | `3456` | `apps/web/app/static/css/_quarantine/wave2e-20260511-185014/ff.pages.css` | already-quarantined, backup-or-legacy-name |
| `already-quarantined` | `True` | `3889` | `apps/web/app/static/css/_quarantine/wave2e-20260511-185014/ff.tokens.css` | already-quarantined, backup-or-legacy-name |
| `already-quarantined` | `True` | `19743` | `apps/web/app/static/css/_quarantine/wave2e-20260511-185014/ff.ui-micropolish.css` | already-quarantined, backup-or-legacy-name |
| `do-not-commit` | `False` | `4605` | `.env` | private-runtime-secret-file |
| `do-not-commit` | `False` | `506` | `.env.local` | private-runtime-secret-file |
| `do-not-commit` | `False` | `1196` | `.env.local.stripe-test` | private-runtime-secret-file |
| `do-not-commit` | `False` | `359` | `.env.production` | private-runtime-secret-file |
| `do-not-commit` | `False` | `71` | `.stripe-local-whsec` | private-runtime-secret-file |
| `generated-restore-or-ignore` | `True` | `140561` | `docs/release-proof/active-repo-map-latest.json` | generated-proof-artifact |
| `generated-restore-or-ignore` | `True` | `26982` | `docs/release-proof/active-repo-map-latest.md` | generated-proof-artifact |
| `generated-restore-or-ignore` | `True` | `323934` | `docs/release-proof/money-flow-script-inventory-latest.json` | generated-proof-artifact, release-proof-history-or-generated-doc |
| `generated-restore-or-ignore` | `True` | `8835` | `docs/release-proof/repo-quarantine-plan-latest.json` | backup-or-legacy-name, generated-proof-artifact, release-proof-history-or-generated-doc |
| `generated-restore-or-ignore` | `True` | `5446` | `docs/release-proof/repo-quarantine-plan-latest.md` | backup-or-legacy-name, generated-proof-artifact, release-proof-history-or-generated-doc |
| `generated-restore-or-ignore` | `True` | `1923` | `docs/release-proof/secret-hygiene-latest.md` | generated-proof-artifact |
| `review` | `True` | `1707` | `.env.example` | example-env-template |
| `review` | `True` | `771` | `.env.production.example` | example-env-template |
| `review` | `True` | `10054` | `docs/release-proof/campaign-asset-map-latest.json` | release-proof-history-or-generated-doc |
| `review` | `True` | `938` | `docs/release-proof/campaign-css-bundle-latest.json` | release-proof-history-or-generated-doc |
| `review` | `True` | `8661` | `docs/release-proof/campaign-css-selector-map-latest.json` | release-proof-history-or-generated-doc |
| `review` | `True` | `2448` | `docs/release-proof/campaign-single-css-bundle-latest.json` | release-proof-history-or-generated-doc |
| `review` | `True` | `1562` | `docs/release-proof/dashboard-single-css-bundle-latest.json` | release-proof-history-or-generated-doc |
| `review` | `True` | `410` | `docs/release-proof/enterprise-launch-gate-latest.json` | release-proof-history-or-generated-doc |
| `review` | `True` | `1013` | `docs/release-proof/futurefunded-production-closeout-v1.md` | release-proof-history-or-generated-doc |
| `review` | `True` | `1221` | `docs/release-proof/login-single-css-bundle-latest.json` | release-proof-history-or-generated-doc |
| `review` | `True` | `1547` | `docs/release-proof/onboarding-single-css-bundle-latest.json` | release-proof-history-or-generated-doc |
| `review` | `True` | `1548` | `docs/release-proof/platform-single-css-bundle-latest.json` | release-proof-history-or-generated-doc |
| `review` | `True` | `16050` | `docs/release-proof/platform-topology-latest.json` | release-proof-history-or-generated-doc |
| `review` | `True` | `3471` | `docs/release-proof/post-action-trust-latest.json` | release-proof-history-or-generated-doc |
| `review` | `True` | `8575` | `docs/release-proof/release-proof-docs-audit-latest.json` | release-proof-history-or-generated-doc |
| `review` | `True` | `6997` | `docs/release-proof/release-proof-docs-audit-latest.md` | release-proof-history-or-generated-doc |
| `review` | `True` | `2428` | `docs/release-proof/surface-stylesheet-map-latest.json` | release-proof-history-or-generated-doc |
| `review` | `False` | `209` | `.env.local.example` | example-env-template |

## Safe next step

Review this plan first. Do not delete active files. Prefer moving stale files into `repo-quarantine/` in a separate commit.
