# FutureFunded Release Proof Docs Audit

## Summary

- `keep`: `6`
- `review`: `13`
- `quarantine-candidate`: `3`

## Files

| Decision | Size | File | Reason |
|---|---:|---|---|
| `keep` | `140561` | `docs/release-proof/active-repo-map-latest.json` | current release/security/quarantine proof |
| `keep` | `26982` | `docs/release-proof/active-repo-map-latest.md` | current release/security/quarantine proof |
| `review` | `10054` | `docs/release-proof/campaign-asset-map-latest.json` | referenced outside docs/release-proof |
| `review` | `938` | `docs/release-proof/campaign-css-bundle-latest.json` | referenced outside docs/release-proof |
| `review` | `8661` | `docs/release-proof/campaign-css-selector-map-latest.json` | referenced outside docs/release-proof |
| `review` | `2448` | `docs/release-proof/campaign-single-css-bundle-latest.json` | referenced outside docs/release-proof |
| `review` | `1562` | `docs/release-proof/dashboard-single-css-bundle-latest.json` | referenced outside docs/release-proof |
| `review` | `410` | `docs/release-proof/enterprise-launch-gate-latest.json` | referenced outside docs/release-proof |
| `quarantine-candidate` | `769` | `docs/release-proof/futurefunded-demo-ready-v1.md` | tracked proof snapshot with no active external references |
| `keep` | `1013` | `docs/release-proof/futurefunded-production-closeout-v1.md` | current release/security/quarantine proof |
| `review` | `1221` | `docs/release-proof/login-single-css-bundle-latest.json` | referenced outside docs/release-proof |
| `review` | `323934` | `docs/release-proof/money-flow-script-inventory-latest.json` | referenced outside docs/release-proof |
| `quarantine-candidate` | `1422` | `docs/release-proof/money-flow-test-proof-latest.md` | tracked proof snapshot with no active external references |
| `quarantine-candidate` | `728` | `docs/release-proof/money-loop-proof.md` | tracked proof snapshot with no active external references |
| `review` | `1547` | `docs/release-proof/onboarding-single-css-bundle-latest.json` | referenced outside docs/release-proof |
| `review` | `1548` | `docs/release-proof/platform-single-css-bundle-latest.json` | referenced outside docs/release-proof |
| `review` | `16050` | `docs/release-proof/platform-topology-latest.json` | referenced outside docs/release-proof |
| `review` | `3471` | `docs/release-proof/post-action-trust-latest.json` | referenced outside docs/release-proof |
| `keep` | `11491` | `docs/release-proof/repo-quarantine-plan-latest.json` | current release/security/quarantine proof |
| `keep` | `6848` | `docs/release-proof/repo-quarantine-plan-latest.md` | current release/security/quarantine proof |
| `keep` | `1923` | `docs/release-proof/secret-hygiene-latest.md` | current release/security/quarantine proof |
| `review` | `2428` | `docs/release-proof/surface-stylesheet-map-latest.json` | referenced outside docs/release-proof |

## Referenced files needing review


### `docs/release-proof/active-repo-map-latest.json`

- `scripts/audit/ff_active_repo_map.py:15:OUT_JSON = ROOT / "docs/release-proof/active-repo-map-latest.json"`
- `scripts/audit/ff_repo_quarantine_plan.py:155:            "docs/release-proof/active-repo-map-latest.json",`
- `scripts/security/ff_secret_hygiene_audit.sh:26:    ':!docs/release-proof/active-repo-map-latest.json' \`

### `docs/release-proof/active-repo-map-latest.md`

- `scripts/audit/ff_active_repo_map.py:16:OUT_MD = ROOT / "docs/release-proof/active-repo-map-latest.md"`
- `scripts/audit/ff_repo_quarantine_plan.py:156:            "docs/release-proof/active-repo-map-latest.md",`
- `scripts/security/ff_secret_hygiene_audit.sh:27:    ':!docs/release-proof/active-repo-map-latest.md' \`

### `docs/release-proof/campaign-asset-map-latest.json`

- `scripts/audit/ff_campaign_asset_map.py:38:out = ROOT / "docs/release-proof/campaign-asset-map-latest.json"`

### `docs/release-proof/campaign-css-bundle-latest.json`

- `scripts/audit/ff_collect_campaign_css_bundle.py:18:PROOF_JSON = Path("docs/release-proof/campaign-css-bundle-latest.json")`

### `docs/release-proof/campaign-css-selector-map-latest.json`

- `scripts/audit/ff_campaign_css_selector_map.py:94:out = ROOT / "docs/release-proof/campaign-css-selector-map-latest.json"`

### `docs/release-proof/campaign-single-css-bundle-latest.json`

- `scripts/release/ff_campaign_single_css_bundle.py:15:PROOF_PATH = ROOT / "docs/release-proof/campaign-single-css-bundle-latest.json"`

### `docs/release-proof/dashboard-single-css-bundle-latest.json`

- `scripts/release/ff_dashboard_single_css_bundle.py:15:PROOF_PATH = ROOT / "docs/release-proof/dashboard-single-css-bundle-latest.json"`

### `docs/release-proof/enterprise-launch-gate-latest.json`

- `scripts/release/ff_enterprise_launch_gate.mjs:628:  path.join(proofDir, "enterprise-launch-gate-latest.json"),`
- `scripts/release/ff_enterprise_launch_gate.mjs:633:console.log("Wrote docs/release-proof/enterprise-launch-gate-latest.json");`

### `docs/release-proof/login-single-css-bundle-latest.json`

- `scripts/release/ff_login_single_css_bundle.py:15:PROOF_PATH = ROOT / "docs/release-proof/login-single-css-bundle-latest.json"`

### `docs/release-proof/money-flow-script-inventory-latest.json`

- `scripts/audit/ff_money_flow_script_inventory.py:10:OUT = ROOT / "docs/release-proof/money-flow-script-inventory-latest.json"`

### `docs/release-proof/onboarding-single-css-bundle-latest.json`

- `scripts/release/ff_onboarding_single_css_bundle.py:15:PROOF_PATH = ROOT / "docs/release-proof/onboarding-single-css-bundle-latest.json"`

### `docs/release-proof/platform-single-css-bundle-latest.json`

- `scripts/release/ff_platform_single_css_bundle.py:15:PROOF_PATH = ROOT / "docs/release-proof/platform-single-css-bundle-latest.json"`

### `docs/release-proof/platform-topology-latest.json`

- `scripts/audit/ff_platform_topology_audit.py:94:out = ROOT / "docs/release-proof/platform-topology-latest.json"`

### `docs/release-proof/post-action-trust-latest.json`

- `scripts/audit/ff_post_action_trust_audit.mjs:7:const proof = "docs/release-proof/post-action-trust-latest.json";`

### `docs/release-proof/repo-quarantine-plan-latest.json`

- `scripts/audit/ff_repo_quarantine_plan.py:12:OUT_JSON = ROOT / "docs/release-proof/repo-quarantine-plan-latest.json"`

### `docs/release-proof/repo-quarantine-plan-latest.md`

- `scripts/audit/ff_repo_quarantine_plan.py:13:OUT_MD = ROOT / "docs/release-proof/repo-quarantine-plan-latest.md"`

### `docs/release-proof/secret-hygiene-latest.md`

- `scripts/audit/ff_repo_quarantine_plan.py:154:            "docs/release-proof/secret-hygiene-latest.md",`
- `scripts/security/ff_secret_hygiene_audit.sh:7:OUT="docs/release-proof/secret-hygiene-latest.md"`
- `scripts/security/ff_secret_hygiene_audit.sh:25:    ':!docs/release-proof/secret-hygiene-latest.md' \`

### `docs/release-proof/surface-stylesheet-map-latest.json`

- `scripts/audit/ff_surface_stylesheet_map.py:47:out = ROOT / "docs/release-proof/surface-stylesheet-map-latest.json"`
