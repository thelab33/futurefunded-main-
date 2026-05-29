# FutureFunded Money Loop Script Map

Generated from filename/content scan.

## High-priority candidates

| Script | Signals |
|---|---|
| `docs/release-proof/tooling-archive/launch-gate-scripts-20260523/ff_dashboard_header_unified_v32.py` | stripe |
| `docs/release-proof/tooling-archive/launch-gate-scripts-20260523/ff_stripe_mercury_refinement_v3.py` | stripe |
| `scripts/audit/backend_inventory.py` | notification, payment, paypal, stripe, webhook |
| `scripts/audit/demo-hardening.mjs` | checkout, donation, ledger, payment, session, stripe |
| `scripts/audit/ff_active_repo_inventory.py` | stripe |
| `scripts/audit/ff_active_repo_map.py` | checkout, donation, ledger, payment, paypal, receipt, session, stripe, webhook |
| `scripts/audit/ff_asset_consolidation_plan.py` | payment |
| `scripts/audit/ff_campaign_checkout_csp_trace.mjs` | checkout, receipt, session |
| `scripts/audit/ff_campaign_contract_audit.py` | checkout, payment |
| `scripts/audit/ff_campaign_conversion_contract_audit.mjs` | checkout, donation, payment |
| `scripts/audit/ff_campaign_conversion_trim_audit.mjs` | checkout, donation, receipt |
| `scripts/audit/ff_campaign_css_inspector.py` | checkout |
| `scripts/audit/ff_campaign_css_selector_map.py` | checkout, payment |
| `scripts/audit/ff_campaign_paint_rhythm_audit.mjs` | checkout, donation, payment |
| `scripts/audit/ff_checkout_continue_ux_audit.mjs` | checkout, receipt, session |
| `scripts/audit/ff_closeout_surface_map.py` | checkout, stripe, webhook |
| `scripts/audit/ff_collect_campaign_css_bundle.py` | checkout, payment |
| `scripts/audit/ff_css_architecture_audit.py` | checkout |
| `scripts/audit/ff_launch_contract_audit.py` | checkout, ledger, payment, paypal, receipt, session, stripe, webhook |
| `scripts/audit/ff_lifecycle_dispatch_drill.py` | checkout, donation, lifecycle |
| `scripts/audit/ff_lifecycle_route_scout.py` | capture, checkout, donation, ledger, lifecycle, paid, payment, paypal, session, stripe, webhook |
| `scripts/audit/ff_money_flow_script_inventory.py` | capture, checkout, donation, ledger, notification, paid, payment, paypal, provider, receipt, session, stripe |
| `scripts/audit/ff_paid_state_forensics.py` | checkout, donation, ledger, lifecycle, paid, payment, receipt, session, stripe, webhook |
| `scripts/audit/ff_platform_topology_audit.py` | checkout, payment |
| `scripts/audit/ff_post_action_trust_audit.mjs` | checkout, donation, ledger, payment, session, stripe |
| `scripts/audit/ff_pre_demo_verify.sh` | checkout, stripe |
| `scripts/audit/ff_prelive_ui_gate.sh` | checkout, donation, provider, stripe |
| `scripts/audit/ff_repo_authority_registry.py` | checkout, payment, provider |
| `scripts/audit/ff_repo_reference_map.py` | checkout, payment, provider |
| `scripts/audit/ff_text_to_donate_launch_audit.mjs` | checkout, provider |
| `scripts/audit/ff_visual_surface_board.mjs` | capture, checkout |
| `scripts/audit/ff_wave10a_sponsor_sales_scout.mjs` | checkout |
| `scripts/audit/ff_wave10b_sponsor_metadata_contract_scout.py` | checkout, ledger, lifecycle, payment, session, stripe |
| `scripts/audit/ff_wave10b_sponsor_metadata_smoke.py` | checkout, session, stripe |
| `scripts/audit/ff_wave2_medium_triage.py` | checkout, lifecycle, notification, provider, receipt |
| `scripts/audit/ff_wave2b_cta_hierarchy_scout.py` | checkout, donation |
| `scripts/audit/ff_wave2c_stale_public_scout.py` | checkout |
| `scripts/audit/ff_wave2e_css_authority_scout.py` | checkout |
| `scripts/audit/ff_wave2f_js_contract_scout.py` | checkout, payment |
| `scripts/audit/ff_wave4_final_funnel_smoke.sh` | checkout, donation, lifecycle |
| `scripts/audit/ff_wave5b_mobile_pixel_qa.mjs` | checkout |
| `scripts/audit/ff_wave5c_stripe_checkout_smoke.py` | checkout, donation, lifecycle, paid, payment, provider, session, stripe |
| `scripts/audit/ff_wave5d_paid_checkout_verify.py` | checkout, ledger, lifecycle, paid, payment, session, stripe |
| `scripts/audit/ff_wave6_founder_demo_scout.mjs` | capture, checkout, donation, payment, receipt, stripe |
| `scripts/audit/ff_wave6c_founder_demo_package.mjs` | donation, paid, payment, receipt, stripe |
| `scripts/audit/ff_wave7a_secret_hygiene.py` | provider, stripe, webhook |
| `scripts/audit/payment_notification_drill.py` | checkout, donation, notification, paid, payment, provider, session, stripe, webhook |
| `scripts/audit/sister_handoff_drill.py` | donation, payment, paypal, session, stripe |
| `scripts/audit_active_frontend.py` | checkout, donation, ledger |
| `scripts/audit_campaign_surface.py` | checkout |
| `scripts/campaign-payment-smoke.mjs` | checkout, donation, payment, paypal, stripe |
| `scripts/capture-campaign-modals.mjs` | capture, checkout, donation |
| `scripts/deploy/purge_cloudflare_assets.sh` | checkout |
| `scripts/extract_campaign_identity_defaults.py` | checkout, provider |
| `scripts/ff_cleanup_repo.py` | provider, stripe |
| `scripts/ff_live_runtime_audit.py` | checkout, payment, session, stripe, webhook |
| `scripts/ff_process_env_audit.py` | stripe, webhook |
| `scripts/ff_repo_audit.py` | capture, checkout, session, stripe, webhook |
| `scripts/ff_verified_local_server.sh` | stripe, webhook |
| `scripts/final_campaign_momentum_premium_audit.py` | checkout, donation |
| `scripts/final_campaign_momentum_signal_strip_audit.py` | checkout |
| `scripts/final_campaign_momentum_visual_audit.py` | checkout |
| `scripts/final_faq_minimal_audit.py` | checkout, receipt |
| `scripts/final_faq_trust_center_audit.py` | checkout, receipt |
| `scripts/final_funnel_functional_audit.py` | checkout, donation, payment, paypal, provider, receipt, stripe, webhook |
| `scripts/final_platform_smoke.py` | checkout |
| `scripts/final_provider_readiness_polish_audit.py` | paypal, provider, receipt, stripe |
| `scripts/final_provider_readiness_v2_audit.py` | paypal, provider, receipt, stripe |
| `scripts/harden_white_label_identity_boundaries.py` | checkout, provider |
| `scripts/launch/ff_full_suite_preflight.mjs` | checkout, payment |
| `scripts/launch/ff_run_full_local_suite.sh` | payment |
| `scripts/ops/ff-founder-demo-checkpoint.sh` | checkout, lifecycle |
| `scripts/ops/ff-postmark-smtp-smoke.py` | ledger, lifecycle, provider, stripe |
| `scripts/polish_campaign_momentum_signal_visual.py` | checkout |
| `scripts/polish_provider_readiness_v2.py` | capture, checkout, donation, notification, payment, paypal, provider, receipt, stripe, webhook |
| `scripts/polish_white_label_provider_readiness.py` | checkout, payment, paypal, provider, receipt, stripe, webhook |
| `scripts/qa_campaign_flagship_smoke.mjs` | checkout, ledger |
| `scripts/qa_campaign_gate.sh` | payment |
| `scripts/qa_conversion_trust_smoke.py` | donation, ledger, payment |
| `scripts/qa_homepage_smoke.mjs` | checkout, ledger, webhook |
| `scripts/qa_payment_contracts.py` | checkout, donation, ledger, paid, payment, session, stripe, webhook |
| `scripts/qa_stripe_webhook_expired_ack.py` | checkout, donation, paid, payment, session, stripe, webhook |
| `scripts/refine_campaign_momentum_premium.py` | checkout, donation |
| `scripts/refine_campaign_momentum_signal_strip.py` | checkout |
| `scripts/refine_faq_bare_minimal.py` | checkout, payment, provider, receipt |
| `scripts/refine_faq_trust_center.py` | checkout, payment, provider, receipt |
| `scripts/release/ff_agency_hardening_gate.sh` | checkout, donation, payment, stripe |
| `scripts/release/ff_campaign_single_css_bundle.py` | checkout |
| `scripts/release/ff_enterprise_launch_gate.mjs` | checkout |
| `scripts/release/ff_final_rehearsal.sh` | checkout, donation, ledger, paid, provider, session |
| `scripts/release/ff_live_donation_readiness_gate.sh` | checkout, donation, session, stripe |
| `scripts/release/ff_paid_state_manual_drill.sh` | checkout, ledger, paid, payment, session, stripe, webhook |
| `scripts/release/ff_payment_mode_audit.py` | capture, checkout, payment, paypal, session, stripe, webhook |
| `scripts/release/ff_receipt_delivery_audit.sh` | checkout, donation, ledger, paid, payment, provider, receipt, session, stripe |
| `scripts/release/ff_release_gate.sh` | checkout |
| `scripts/release/ff_run_prelive_conversion_suite.sh` | capture, checkout, donation, stripe |
| `scripts/release/ff_sister_today_closeout.sh` | stripe |
| `scripts/release/ff_test_donation_readiness_gate.sh` | checkout, donation, ledger, payment, session, stripe |
| `scripts/release/ff_verify_release_claims.sh` | checkout |
| `scripts/release/futurefunded_release_gate.py` | stripe |
| `scripts/release/inspect-stripe-webhook-readiness.sh` | payment, stripe, webhook |
| `scripts/release/verify-analytics-events.mjs` | capture, checkout, provider |
| `scripts/release/verify-checkout-flow-stability.sh` | checkout, donation, payment |
| `scripts/release/verify-conversion-behavior.mjs` | capture, checkout, donation, payment, paypal, session, stripe |
| `scripts/release/verify-referral-attribution.mjs` | checkout |
| `scripts/release/verify-stripe-network.sh` | checkout, session, stripe |
| `scripts/release/verify-stripe-test-checkout.mjs` | checkout, paid, payment, session, stripe |
| `scripts/remove_sponsor_signal_strip.py` | checkout |
| `scripts/repo/finalize_ui_core_blockers.py` | capture, checkout |
| `scripts/repo/find_money_loop_scripts.py` | capture, checkout, donation, invoice, ledger, lifecycle, notification, paid, payment, paypal, provider, receipt, session, stripe, webhook |
| `scripts/run_local_stripe.sh` | stripe, webhook |
| `scripts/run_public_preview.sh` | payment |
| `scripts/security/ff_secret_hygiene_audit.sh` | stripe |
| `scripts/security/ff_secret_scan_postmark.sh` | stripe |
| `scripts/setup_sister_demo.py` | checkout, payment, paypal, stripe |
| `scripts/smoke_product_pages.py` | checkout, donation, ledger |
| `scripts/test_product_functionality.mjs` | checkout, donation |
| `scripts/verify-campaign-launch.mjs` | checkout, paypal, stripe |
| `scripts/verify-campaign-modals.mjs` | checkout, donation, payment |
| `scripts/verify-campaign-payments.mjs` | checkout, donation, payment, paypal, provider, session, stripe |
| `scripts/verify-header-convergence.mjs` | checkout |
| `scripts/verify-homepage-surface.mjs` | paypal, stripe |
| `scripts/verify/ff_campaign_v1_authority_money_loop.mjs` | checkout, donation, ledger, paid, payment, session, stripe |
| `scripts/verify/ff_cinematic_money_loop.mjs` | checkout, ledger, paid, payment, session, stripe |
| `scripts/verify/ff_css_v1_authority_check.mjs` | checkout |
| `scripts/verify/ff_real_stripe_money_loop_hybrid.mjs` | checkout, ledger, paid, payment, session, stripe, webhook |
| `scripts/verify_campaign_surface.py` | capture, checkout, donation, payment |
| `docs/release-proof/tooling-archive/launch-gate-scripts-20260523/ff_dashboard_header_surgical_reset.py` | capture |
| `docs/release-proof/tooling-archive/launch-gate-scripts-20260523/ff_live_quality_gate.py` | capture |
| `scripts/audit/ff_campaign_enterprise_sms_audit.mjs` | webhook |
| `scripts/audit/ff_dashboard_flash_root_cause_audit.py` | capture |
| `scripts/audit/ff_lifecycle_message_drill.py` | lifecycle, provider |
| `scripts/audit/ff_onboarding_executive_audit.mjs` | provider |
| `scripts/audit/ff_receipt_lifecycle_contract.py` | lifecycle, receipt |
| `scripts/audit/ff_root_platform_release_contract.mjs` | donation |
| `scripts/audit/ff_wave2d_lifecycle_provider_readiness.py` | donation, ledger, lifecycle, provider |
| `scripts/audit/ff_wave3_operator_polish_scout.py` | ledger |
| `scripts/audit/operator_notification_outbox_drill.py` | donation, ledger, notification, provider, session |
| `scripts/audit/platform-ops-hardening.mjs` | donation, ledger |
| `scripts/capture-campaign-screenshot.mjs` | capture |
| `scripts/capture-homepage-screenshot.mjs` | capture |
| `scripts/capture_live_rhythm_screenshots.sh` | capture |
| `scripts/capture_product_screenshots.mjs` | capture |
| `scripts/final_campaign_identity_extraction_audit.py` | provider |
| `scripts/final_campaign_momentum_os_audit.py` | donation |
| `scripts/final_campaign_profile_audit.py` | donation |
| `scripts/final_release_gate.py` | provider |
| `scripts/final_sponsor_confirmation_audit.py` | notification |
| `scripts/final_sponsor_operator_notification_audit.py` | notification |
| `scripts/final_white_label_active_surface_audit.py` | provider |
| `scripts/final_white_label_identity_boundaries_audit.py` | provider |
| `scripts/finalize_active_white_label_cleanup.py` | provider |
| `scripts/ops/ff-email-doctor.sh` | lifecycle, provider |
| `scripts/qa_operator_access_control.py` | donation, ledger |
| `scripts/qa_operator_dashboard_smoke.mjs` | donation, ledger |
| `scripts/qa_operator_login_smoke.py` | ledger, session |
| `scripts/qa_trust_proof_visual.mjs` | ledger |
| `scripts/release/ff_dashboard_single_css_bundle.py` | provider |
| `scripts/repo/create_active_surface_repo.py` | capture |
| `scripts/verify-homepage-launch.mjs` | capture |

## Non-executable/reference docs

- `docs/LAUNCH_BACKLOG.md` — checkout, notification, paid, payment, provider, receipt, session, stripe
- `docs/PRODUCTION_HANDOFF_CHECKLIST.md` — checkout, donation, ledger, payment, session, stripe
- `docs/SISTER_DEMO_RUNBOOK.md` — checkout, donation, ledger, payment
- `docs/audits/POST_DEMO_NEXT_PHASE.md` — capture, checkout, donation, ledger, payment, receipt, session, stripe, webhook
- `docs/audits/backend-inventory/backend-inventory.md` — capture, checkout, donation, ledger, payment, paypal, provider, session, stripe, webhook
- `docs/demo/FOUNDER_DEMO_SCRIPT.md` — checkout, donation, ledger, payment, provider
- `docs/deploy/DEPLOY_PREVIEW_RUNBOOK.md` — ledger, paypal, provider, stripe, webhook
- `docs/final-launch-qa-checkpoint.md` — ledger, payment, stripe, webhook
- `docs/final-launch-qa-post-wave8b.md` — checkout, donation, lifecycle, stripe
- `docs/founder-demo-polish-plan.md` — checkout, donation, ledger, lifecycle, payment, provider, session, stripe
- `docs/founder-demo-walkthrough.md` — checkout, donation, ledger, lifecycle, paid, payment, session, stripe
- `docs/launch-closeout/live-roadmap.md` — checkout, ledger, payment, stripe
- `docs/launch-closeout/local-roadmap.md` — checkout, ledger, payment, stripe
- `docs/launch-closeout/sister-today-roadmap.md` — checkout, ledger, payment, stripe
- `docs/launch-readiness-checkpoint.md` — checkout, donation, lifecycle, provider, stripe
- `docs/launch-risk-register.md` — checkout, lifecycle, notification, provider, stripe
- `docs/live-demo-checklist.md` — checkout, stripe
- `docs/release-map.md` — payment
- `docs/release-proof/active-repo-map-latest.md` — capture, checkout, donation, ledger, paid, payment, paypal, provider, receipt, session, stripe, webhook
- `docs/release-proof/css-authority-cleanup-20260521.md` — checkout
- `docs/release-proof/futurefunded-production-closeout-v1.md` — checkout, donation, ledger, paid, session, stripe
- `docs/release-proof/repo-quarantine-plan-latest.md` — stripe
- `docs/release-proof/secret-hygiene-latest.md` — provider, stripe, webhook
- `docs/release-proof/ui-core-final-blockers-20260523024222.md` — checkout
- `docs/release-proof/ui-core-quarantine-apply-20260523015432.md` — checkout, donation, payment, provider
- `docs/release-proof/ui-core-quarantine-plan.md` — checkout, donation, payment, provider
- `docs/release-proof/ui-core-quarantine-safe-20260523021137.md` — checkout, donation, payment, provider
- `docs/release-proof/ui-core-quarantine-safe-20260523021333.md` — checkout, donation, payment, provider
- `docs/repo-authority.md` — checkout, payment, provider
- `docs/sister-ui-review-checklist.md` — checkout, donation, receipt, stripe, webhook
- `docs/wave2e-2f-closeout.md` — checkout, payment
- `docs/wave5a-operator-ux-polish.md` — payment, provider
- `docs/wave5d-money-loop-proof.md` — checkout, donation, ledger, lifecycle, paid, payment, provider, session, stripe
- `docs/wave5e-email-delivery-proof.md` — donation, lifecycle, provider, stripe, webhook
- `docs/frontend/VISUAL_SYSTEM_AUTHORITY.md` — donation
- `docs/release-proof/dashboard-js-authority-audit.md` — donation, ledger
