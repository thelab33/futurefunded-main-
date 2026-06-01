# FutureFunded Donation Ops Readiness

Generated: 20260601011807

## Current proof status

- UI/visual/payment-opening proof is green.
- This report audits whether completed donations can be stored, emailed, exported, and reviewed.

## Backend files touching money, email, webhooks, dashboard, exports

```text
apps/api/app/routers/payments.py
apps/api/app/routers/sponsors.py
apps/api/app/schemas/events.py
apps/api/app/schemas/onboarding.py
apps/api/app/schemas/payments.py
apps/api/app/schemas/sponsors.py
apps/api/app/services/email_service.py
apps/api/app/services/paypal_service.py
apps/api/app/services/sponsor_service.py
apps/api/app/services/stripe_service.py
apps/api/app/tasks/exports.py
apps/api/app/tasks/receipts.py
apps/api/app/tasks/sponsor_notifications.py
apps/api/routes/web_sponsors.py
apps/web/app/blueprints/sponsors/__pycache__/routes.cpython-313.pyc
apps/web/app/blueprints/sponsors/__pycache__/services.cpython-313.pyc
apps/web/app/blueprints/sponsors/routes.py
apps/web/app/blueprints/sponsors/services.py
apps/web/app/domain/payments.py
apps/web/app/domain/__pycache__/sponsor.cpython-313.pyc
apps/web/app/domain/sponsor.py
apps/web/app/services/ff_transactional_email.py
apps/web/app/services/operator_notifications.py
apps/web/app/services/__pycache__/ff_transactional_email.cpython-313.pyc
apps/web/app/services/__pycache__/operator_notifications.cpython-313.pyc
apps/web/app/services/__pycache__/sponsor_lead_repository.cpython-313.pyc
apps/web/app/services/sponsor_confirmation_notifications.py
apps/web/app/services/sponsor_confirmation_payload.py
apps/web/app/services/sponsor_lead_repository.py
apps/web/app/services/sponsor_operator_notifications.py
apps/web/app/services/sponsor_operator_payload.py
apps/web/app/services/sponsor_package_metadata.py
apps/web/app/static/js/ff-checkout-direct.js
apps/web/app/static/js/ff-donation-payload-firewall.js
apps/web/app/static/js/ff-embedded-checkout.js
apps/web/app/static/js/ff-operator-dashboard.js
apps/web/app/static/js/ff-sponsor-modal-contract.js
apps/web/app/templates/_partials/ff_dashboard_launch_assistant.html
apps/web/app/templates/platform/dashboard.html
apps/web/app/templates/platform/dashboard_locked.html
apps/web/app/templates/platform/_sponsor_package_preview.html
apps/web/app/templates/platform/_sponsor_queue_preview.html
apps/web/app/viewmodels/campaign_vm.py
apps/web/app/viewmodels/onboarding_vm.py
apps/web/app/viewmodels/platform_vm.py
apps/web/app/viewmodels/__pycache__/campaign_vm.cpython-313.pyc
apps/web/app/viewmodels/__pycache__/onboarding_vm.cpython-313.pyc
apps/web/app/viewmodels/__pycache__/platform_vm.cpython-313.pyc
scripts/campaign-payment-smoke.mjs
scripts/campaign-payment-smoke-safe.mjs
scripts/create_operator_user.py
scripts/ops/ff-email-doctor.sh
scripts/refactor/ff_migrate_dashboard_to_shell.py
scripts/release/ff_dashboard_screenshot_board.mjs
scripts/release/ff_dashboard_single_css_bundle.py
scripts/release/ff_live_donation_readiness_gate.sh
scripts/release/ff_payment_mode_audit.py
scripts/release/ff_receipt_delivery_audit.sh
scripts/release/ff_test_donation_readiness_gate.sh
scripts/release/inspect-stripe-webhook-readiness.sh
scripts/release/payment_readiness_gate.py
scripts/release/verify-checkout-flow-stability.sh
scripts/release/verify-stripe-network.sh
scripts/release/verify-stripe-test-checkout.mjs
scripts/run_local_stripe.sh
scripts/verify/ff_real_stripe_money_loop_hybrid.mjs
```

## Route and handler grep

```text
apps/api/asgi.py:6:from apps.api.routes.web_sponsors import router as sponsors_router
apps/api/asgi.py:13:    # exposes GET /sponsors in the same ASGI app CI boots.
apps/api/asgi.py:15:        app.include_router(sponsors_router)
apps/api/routes/web_sponsors.py:6:@router.get("/sponsors")
apps/api/routes/web_sponsors.py:7:def get_sponsors():
apps/api/routes/web_sponsors.py:8:    return {"ok": True, "resource": "sponsors", "tiers": [], "wall": []}
apps/api/app/services/paypal_service.py:10:_ALLOWED_CHECKOUT_KINDS = {"donation", "sponsor", "membership"}
apps/api/app/services/paypal_service.py:99:    webhook_id: str = ""
apps/api/app/services/paypal_service.py:118:            return "https://api-m.paypal.com"
apps/api/app/services/paypal_service.py:119:        return "https://api-m.sandbox.paypal.com"
apps/api/app/services/paypal_service.py:123:            "provider": "paypal",
apps/api/app/services/paypal_service.py:137:        checkout_kind = _clean(payload.get("checkout_kind"), "donation").lower()
apps/api/app/services/paypal_service.py:138:        if checkout_kind not in _ALLOWED_CHECKOUT_KINDS:
apps/api/app/services/paypal_service.py:139:            checkout_kind = "donation"
apps/api/app/services/paypal_service.py:141:        donor_name = _truncate(_clean(payload.get("donor_name")), 120)
apps/api/app/services/paypal_service.py:142:        donor_email = _truncate(_clean(payload.get("donor_email")), 254)
apps/api/app/services/paypal_service.py:143:        donor_message = _truncate(_clean(payload.get("donor_message")), 255)
apps/api/app/services/paypal_service.py:150:            f"kind:{checkout_kind}",
apps/api/app/services/paypal_service.py:154:        if donor_email:
apps/api/app/services/paypal_service.py:155:            custom_fields.append(f"email:{donor_email}")
apps/api/app/services/paypal_service.py:170:        if donor_name:
apps/api/app/services/paypal_service.py:171:            note_parts.append(f"Donor: {donor_name}")
apps/api/app/services/paypal_service.py:172:        if donor_email:
apps/api/app/services/paypal_service.py:173:            note_parts.append(f"Email: {donor_email}")
apps/api/app/services/paypal_service.py:174:        if donor_message:
apps/api/app/services/paypal_service.py:175:            note_parts.append(f"Message: {donor_message}")
apps/api/app/services/paypal_service.py:253:                "provider": "paypal",
apps/api/app/services/paypal_service.py:262:                "provider": "paypal",
apps/api/app/services/paypal_service.py:272:                "/v2/checkout/orders",
apps/api/app/services/paypal_service.py:284:                "provider": "paypal",
apps/api/app/services/paypal_service.py:293:                "provider": "paypal",
apps/api/app/services/paypal_service.py:305:                "provider": "paypal",
apps/api/app/services/paypal_service.py:315:                "provider": "paypal",
apps/api/app/services/paypal_service.py:326:                f"/v2/checkout/orders/{safe_order_id}/capture",
apps/api/app/services/paypal_service.py:339:                payments = (purchase_units[0] or {}).get("payments") or {}
apps/api/app/services/paypal_service.py:340:                captures = payments.get("captures") or []
apps/api/app/services/paypal_service.py:346:                "provider": "paypal",
apps/api/app/services/paypal_service.py:355:                "provider": "paypal",
apps/api/app/services/paypal_service.py:363:    def normalize_webhook_event(
apps/api/app/services/paypal_service.py:378:            "provider": "paypal",
apps/api/app/services/paypal_service.py:383:            "webhook_id_present": bool(self.webhook_id),
apps/api/app/services/paypal_service.py:389:        transmission_time = _clean(safe_headers.get("paypal-transmission-time"))
apps/api/app/services/paypal_service.py:390:        transmission_sig = _clean(safe_headers.get("paypal-transmission-sig"))
apps/api/app/services/paypal_service.py:391:        cert_url = _clean(safe_headers.get("paypal-cert-url"))
apps/api/app/services/paypal_service.py:392:        auth_algo = _clean(safe_headers.get("paypal-auth-algo"))
apps/api/app/services/paypal_service.py:396:            and self.webhook_id
apps/api/app/services/paypal_service.py:408:            elif not self.webhook_id:
apps/api/app/services/paypal_service.py:409:                base["verification_status"] = "webhook_id_missing"
apps/api/app/services/paypal_service.py:424:                "webhook_id": self.webhook_id,
apps/api/app/services/paypal_service.py:425:                "webhook_event": safe_payload,
apps/api/app/services/paypal_service.py:430:                "/v1/notifications/verify-webhook-signature",
apps/api/app/services/email_service.py:14:class EmailMessage:
apps/api/app/services/email_service.py:28:class EmailService:
apps/api/app/services/email_service.py:29:    sender_email: str = "support@getfuturefunded.com"
apps/api/app/services/email_service.py:36:            return f"{self.sender_name} <{self.sender_email}>"
apps/api/app/services/email_service.py:37:        return self.sender_email
apps/api/app/services/email_service.py:39:    def build_receipt_email(
apps/api/app/services/email_service.py:41:        to_email: str,
apps/api/app/services/email_service.py:45:    ) -> EmailMessage:
apps/api/app/services/email_service.py:56:            f"If you need help, reply to {self.sender_email}.\n\n"
apps/api/app/services/email_service.py:65:            f"<p>If you need help, reply to {self.sender_email}.</p>"
apps/api/app/services/email_service.py:69:        return EmailMessage(
apps/api/app/services/email_service.py:70:            to=to_email,
apps/api/app/services/email_service.py:74:            reply_to=self.sender_email,
apps/api/app/services/email_service.py:77:    def build_sponsor_lead_email(
apps/api/app/services/email_service.py:79:        notify_email: str,
apps/api/app/services/email_service.py:81:    ) -> EmailMessage:
apps/api/app/services/email_service.py:83:        sponsor_tier = _clean(lead.get("sponsor_tier"), "Unspecified tier")
apps/api/app/services/email_service.py:86:        contact_email = _clean(lead.get("contact_email"))
apps/api/app/services/email_service.py:90:        subject = f"New sponsor lead for {campaign_slug}: {business_name}"
apps/api/app/services/email_service.py:92:            f"New sponsor lead received.\n\n"
apps/api/app/services/email_service.py:95:            f"Email: {contact_email}\n"
apps/api/app/services/email_service.py:97:            f"Tier: {sponsor_tier}\n"
apps/api/app/services/email_service.py:103:            f"<p><strong>New sponsor lead received.</strong></p>"
apps/api/app/services/email_service.py:106:            f"<strong>Email:</strong> {contact_email}<br>"
apps/api/app/services/email_service.py:108:            f"<strong>Tier:</strong> {sponsor_tier}<br>"
apps/api/app/services/email_service.py:113:        return EmailMessage(
apps/api/app/services/email_service.py:114:            to=notify_email,
apps/api/app/services/email_service.py:118:            reply_to=contact_email or self.sender_email,
apps/api/app/services/email_service.py:121:    def send(self, message: EmailMessage) -> dict[str, Any]:
apps/api/app/services/sponsor_service.py:29:def _normalize_email(value: Any) -> str:
apps/api/app/services/sponsor_service.py:45:        "featured sponsor": "Featured Sponsor",
apps/api/app/services/sponsor_service.py:47:        "community sponsor": "Community Sponsor",
apps/api/app/services/sponsor_service.py:49:        "supporting sponsor": "Supporting Sponsor",
apps/api/app/services/sponsor_service.py:54:def _looks_like_email(value: str) -> bool:
apps/api/app/services/sponsor_service.py:60:    notify_email: str = "support@getfuturefunded.com"
apps/api/app/services/sponsor_service.py:64:        sponsor_tier = _normalize_tier(payload.get("sponsor_tier"))
apps/api/app/services/sponsor_service.py:70:            "contact_email": _normalize_email(payload.get("contact_email")),
apps/api/app/services/sponsor_service.py:72:            "sponsor_tier": sponsor_tier,
apps/api/app/services/sponsor_service.py:85:        if not normalized["contact_email"]:
apps/api/app/services/sponsor_service.py:86:            errors.append("contact_email is required")
apps/api/app/services/sponsor_service.py:87:        elif not _looks_like_email(normalized["contact_email"]):
apps/api/app/services/sponsor_service.py:88:            errors.append("contact_email must be a valid email")
apps/api/app/services/sponsor_service.py:95:        if normalized["sponsor_tier"] and normalized["sponsor_tier"] not in _ALLOWED_TIERS:
apps/api/app/services/sponsor_service.py:96:            errors.append("sponsor_tier must match an available sponsor package")
apps/api/app/services/sponsor_service.py:115:            "notify_email": _truncate(self.notify_email, 254, "support@getfuturefunded.com"),
apps/api/app/services/sponsor_service.py:119:    def sponsor_wall_item(self, payload: dict[str, Any]) -> dict[str, Any]:
apps/api/app/services/sponsor_service.py:121:        tier = normalized["sponsor_tier"] or "Sponsor"
apps/api/app/services/stripe_service.py:8:    import stripe as stripe_sdk  # type: ignore
apps/api/app/services/stripe_service.py:10:    stripe_sdk = None
apps/api/app/services/stripe_service.py:32:_ALLOWED_CHECKOUT_KINDS = {"donation", "sponsor", "membership"}
apps/api/app/services/stripe_service.py:86:    return "Stripe could not create a payment intent right now."
apps/api/app/services/stripe_service.py:110:    webhook_secret: str = ""
apps/api/app/services/stripe_service.py:115:        return stripe_sdk is not None
apps/api/app/services/stripe_service.py:124:            "provider": "stripe",
apps/api/app/services/stripe_service.py:142:        donor_email = _truncate(_clean(payload.get("donor_email")), 254)
apps/api/app/services/stripe_service.py:143:        donor_name = _truncate(_clean(payload.get("donor_name")), 120)
apps/api/app/services/stripe_service.py:144:        donor_message = _truncate(_clean(payload.get("donor_message")), 500)
apps/api/app/services/stripe_service.py:147:        checkout_kind = _clean(payload.get("checkout_kind"), "donation").lower()
apps/api/app/services/stripe_service.py:148:        if checkout_kind not in _ALLOWED_CHECKOUT_KINDS:
apps/api/app/services/stripe_service.py:149:            checkout_kind = "donation"
apps/api/app/services/stripe_service.py:154:                "checkout_kind": _truncate(checkout_kind, 100),
apps/api/app/services/stripe_service.py:155:                "donor_email": _truncate(donor_email, 500),
apps/api/app/services/stripe_service.py:156:                "donor_name": _truncate(donor_name, 500),
apps/api/app/services/stripe_service.py:158:                "donor_message": _truncate(donor_message, 500),
apps/api/app/services/stripe_service.py:169:            "automatic_payment_methods": {"enabled": True},
apps/api/app/services/stripe_service.py:171:            "receipt_email": donor_email or None,
apps/api/app/services/stripe_service.py:181:                "provider": "stripe",
apps/api/app/services/stripe_service.py:190:                "provider": "stripe",
apps/api/app/services/stripe_service.py:199:                "provider": "stripe",
apps/api/app/services/stripe_service.py:206:            stripe_sdk.api_key = self.secret_key
apps/api/app/services/stripe_service.py:207:            intent = stripe_sdk.PaymentIntent.create(**intent_payload)
apps/api/app/services/stripe_service.py:211:                "provider": "stripe",
apps/api/app/services/stripe_service.py:212:                "status": getattr(intent, "status", "requires_payment_method"),
apps/api/app/services/stripe_service.py:220:                "provider": "stripe",
apps/api/app/services/stripe_service.py:227:    def normalize_webhook_event(
apps/api/app/services/stripe_service.py:240:            "provider": "stripe",
apps/api/app/services/stripe_service.py:244:            "webhook_secret_present": bool(self.webhook_secret),
apps/api/app/services/stripe_service.py:252:        can_verify = bool(self.sdk_available and self.webhook_secret and signature and raw_body)
apps/api/app/services/stripe_service.py:255:            if signature and self.webhook_secret and not self.sdk_available:
apps/api/app/services/stripe_service.py:257:            elif signature and not self.webhook_secret:
apps/api/app/services/stripe_service.py:259:            elif signature and self.webhook_secret and not raw_body:
apps/api/app/services/stripe_service.py:266:            verified_event = stripe_sdk.Webhook.construct_event(
apps/api/app/services/stripe_service.py:269:                secret=self.webhook_secret,
apps/api/app/services/stripe_service.py:276:                "provider": "stripe",
apps/api/app/services/stripe_service.py:280:                "webhook_secret_present": True,
apps/api/app/tasks/receipts.py:6:from app.services.email_service import EmailService
apps/api/app/tasks/receipts.py:11:    email_service: EmailService
apps/api/app/tasks/receipts.py:16:        to_email: str,
apps/api/app/tasks/receipts.py:21:        message = self.email_service.build_receipt_email(
apps/api/app/tasks/receipts.py:22:            to_email=to_email,
apps/api/app/tasks/receipts.py:27:        result = self.email_service.send(message)
apps/api/app/tasks/receipts.py:30:            "task": "receipt_email",
apps/api/app/tasks/receipts.py:35:def queue_receipt_email(
apps/api/app/tasks/receipts.py:37:    to_email: str,
apps/api/app/tasks/receipts.py:41:    sender_email: str = "support@getfuturefunded.com",
apps/api/app/tasks/receipts.py:46:        email_service=EmailService(
apps/api/app/tasks/receipts.py:47:            sender_email=sender_email,
apps/api/app/tasks/receipts.py:53:        to_email=to_email,
apps/api/app/tasks/exports.py:28:def export_rows_to_csv(
apps/api/app/tasks/exports.py:31:    prefix: str = "futurefunded-export",
apps/api/app/tasks/sponsor_notifications.py:6:from app.services.email_service import EmailService
apps/api/app/tasks/sponsor_notifications.py:11:    email_service: EmailService
apps/api/app/tasks/sponsor_notifications.py:16:        notify_email: str,
apps/api/app/tasks/sponsor_notifications.py:19:        message = self.email_service.build_sponsor_lead_email(
apps/api/app/tasks/sponsor_notifications.py:20:            notify_email=notify_email,
apps/api/app/tasks/sponsor_notifications.py:23:        result = self.email_service.send(message)
apps/api/app/tasks/sponsor_notifications.py:26:            "task": "sponsor_notification",
apps/api/app/tasks/sponsor_notifications.py:31:def queue_sponsor_notification(
apps/api/app/tasks/sponsor_notifications.py:33:    notify_email: str,
apps/api/app/tasks/sponsor_notifications.py:35:    sender_email: str = "support@getfuturefunded.com",
apps/api/app/tasks/sponsor_notifications.py:40:        email_service=EmailService(
apps/api/app/tasks/sponsor_notifications.py:41:            sender_email=sender_email,
apps/api/app/tasks/sponsor_notifications.py:47:        notify_email=notify_email,
apps/api/app/routers/sponsors.py:8:from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
apps/api/app/routers/sponsors.py:10:from app.services.sponsor_service import SponsorService
apps/api/app/routers/sponsors.py:28:    contact_email: EmailStr
apps/api/app/routers/sponsors.py:30:    sponsor_tier: str = Field(default="", max_length=80)
apps/api/app/routers/sponsors.py:34:    @field_validator("business_name", "contact_name", "contact_phone", "sponsor_tier", "message")
apps/api/app/routers/sponsors.py:50:def _notify_email() -> str:
apps/api/app/routers/sponsors.py:59:    return SponsorService(notify_email=_notify_email())
apps/api/app/routers/sponsors.py:77:async def create_sponsor_lead(
apps/api/app/routers/sponsors.py:92:async def sponsor_wall_item(
apps/api/app/routers/sponsors.py:99:    item = _service().sponsor_wall_item(payload.model_dump(mode="json"))
apps/api/app/routers/onboarding.py:6:from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
apps/api/app/routers/onboarding.py:24:    operator_email: EmailStr | None = None
apps/api/app/routers/onboarding.py:27:    primary_sponsor_package: str = Field(default="", max_length=200)
apps/api/app/routers/onboarding.py:28:    payment_stack: str = Field(default="", max_length=120)
apps/api/app/routers/onboarding.py:36:        "primary_sponsor_package",
apps/api/app/routers/onboarding.py:37:        "payment_stack",
apps/api/app/routers/onboarding.py:43:    @field_validator("operator_email", mode="before")
apps/api/app/routers/onboarding.py:45:    def normalize_operator_email(cls, value: Any) -> Any:
apps/api/app/routers/onboarding.py:75:        payload.operator_email and f"Operator email: {payload.operator_email}",
apps/api/app/routers/onboarding.py:76:        payload.primary_sponsor_package and f"Sponsor package: {payload.primary_sponsor_package}",
apps/api/app/routers/onboarding.py:77:        payload.payment_stack and f"Payments: {payload.payment_stack}",
apps/api/app/routers/onboarding.py:88:    if not payload.operator_email:
apps/api/app/routers/onboarding.py:89:        missing.append("operator_email")
apps/api/app/routers/onboarding.py:103:    if data.get("operator_email") is None:
apps/api/app/routers/onboarding.py:104:        data["operator_email"] = ""
apps/api/app/routers/onboarding.py:109:    return not _missing_fields(payload) and payload.goal > 0 and bool(payload.payment_stack)
apps/api/app/routers/payments.py:10:from app.schemas.payments import (
apps/api/app/routers/payments.py:21:from app.services.paypal_service import PayPalService
apps/api/app/routers/payments.py:22:from app.services.stripe_service import StripeService
apps/api/app/routers/payments.py:29:def _stripe_service() -> StripeService:
apps/api/app/routers/payments.py:33:        webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET", "").strip(),
apps/api/app/routers/payments.py:38:def _paypal_service() -> PayPalService:
apps/api/app/routers/payments.py:42:        webhook_id=os.getenv("PAYPAL_WEBHOOK_ID", "").strip(),
apps/api/app/routers/payments.py:100:def _payment_config_payload() -> dict[str, Any]:
apps/api/app/routers/payments.py:101:    stripe = _stripe_service()
apps/api/app/routers/payments.py:102:    paypal = _paypal_service()
apps/api/app/routers/payments.py:104:    stripe_public = stripe.public_config()
apps/api/app/routers/payments.py:105:    paypal_public = paypal.public_config()
apps/api/app/routers/payments.py:110:            "stripe": PaymentProviderPublicConfig(**stripe_public),
apps/api/app/routers/payments.py:111:            "paypal": PaymentProviderPublicConfig(**paypal_public),
apps/api/app/routers/payments.py:117:async def payment_config(
apps/api/app/routers/payments.py:126:    return PaymentConfigOut(**_payment_config_payload())
apps/api/app/routers/payments.py:129:@router.post("/stripe/intent", response_model=StripeIntentOut)
apps/api/app/routers/payments.py:130:async def create_stripe_intent(
apps/api/app/routers/payments.py:136:    result = _stripe_service().create_intent_response(payload.model_dump())
apps/api/app/routers/payments.py:140:@router.post("/paypal/order", response_model=PayPalOrderOut)
apps/api/app/routers/payments.py:141:async def create_paypal_order(
apps/api/app/routers/payments.py:147:    result = _paypal_service().create_order_response(payload.model_dump())
apps/api/app/routers/payments.py:151:@router.post("/paypal/capture", response_model=PayPalCaptureOut)
apps/api/app/routers/payments.py:152:async def capture_paypal_order(
apps/api/app/routers/payments.py:158:    result = _paypal_service().capture_order_response(payload.order_id)
apps/api/app/routers/payments.py:162:@router.post("/webhooks/stripe", response_model=WebhookEventOut)
apps/api/app/routers/payments.py:163:async def stripe_webhook(
apps/api/app/routers/payments.py:166:    stripe_signature: str | None = Header(default=None, alias="stripe-signature"),
apps/api/app/routers/payments.py:175:    service = _stripe_service()
apps/api/app/routers/payments.py:177:        service.normalize_webhook_event,
apps/api/app/routers/payments.py:180:        signature=stripe_signature,
apps/api/app/routers/payments.py:192:@router.post("/webhooks/paypal", response_model=WebhookEventOut)
apps/api/app/routers/payments.py:193:async def paypal_webhook(
apps/api/app/routers/payments.py:196:    paypal_transmission_id: str | None = Header(default=None, alias="paypal-transmission-id"),
apps/api/app/routers/payments.py:205:    service = _paypal_service()
apps/api/app/routers/payments.py:207:        service.normalize_webhook_event,
apps/api/app/routers/payments.py:210:        transmission_id=paypal_transmission_id,
apps/api/app/main.py:16:from app.routers.payments import router as payments_router
apps/api/app/main.py:17:from app.routers.sponsors import router as sponsors_router
apps/api/app/main.py:108:        description="Service layer for FutureFunded payments, sponsors, onboarding, and analytics.",
apps/api/app/main.py:137:    app.include_router(payments_router, prefix="/payments", tags=["payments"])
apps/api/app/main.py:138:    app.include_router(sponsors_router, prefix="/sponsors", tags=["sponsors"])
apps/api/app/schemas/sponsors.py:7:from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
apps/api/app/schemas/sponsors.py:23:    contact_email: EmailStr
apps/api/app/schemas/sponsors.py:25:    sponsor_tier: str = Field(default="", max_length=80)
apps/api/app/schemas/sponsors.py:29:    @field_validator("business_name", "contact_name", "contact_phone", "sponsor_tier", "message")
apps/api/app/schemas/sponsors.py:51:    contact_email: str = Field(..., min_length=1, max_length=254)
apps/api/app/schemas/sponsors.py:53:    sponsor_tier: str = Field(default="", max_length=80)
apps/api/app/schemas/sponsors.py:63:        "contact_email",
apps/api/app/schemas/sponsors.py:65:        "sponsor_tier",
apps/api/app/schemas/sponsors.py:90:    notify_email: str | None = None
apps/api/app/schemas/onboarding.py:5:from pydantic import BaseModel, ConfigDict, EmailStr, Field
apps/api/app/schemas/onboarding.py:15:    operator_email: EmailStr | None = None
apps/api/app/schemas/onboarding.py:18:    primary_sponsor_package: str = ""
apps/api/app/schemas/onboarding.py:19:    payment_stack: str = ""
apps/api/app/schemas/events.py:8:from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
apps/api/app/schemas/events.py:121:    event_source: Literal["stripe", "paypal"] = "stripe"
apps/api/app/schemas/events.py:123:    checkout_kind: Literal["donation", "sponsor", "membership"] = "donation"
apps/api/app/schemas/events.py:131:    def normalize_payment_event_source(cls, value: Any) -> str:
apps/api/app/schemas/events.py:132:        cleaned = _clean(value, "stripe").lower()
apps/api/app/schemas/events.py:133:        return cleaned or "stripe"
apps/api/app/schemas/events.py:137:    def trim_payment_text(cls, value: Any) -> str | None:
apps/api/app/schemas/events.py:157:    sponsor_tier: str | None = Field(default=None, max_length=80)
apps/api/app/schemas/events.py:159:    contact_email: EmailStr | None = None
apps/api/app/schemas/events.py:164:    def normalize_sponsor_event_source(cls, value: Any) -> str:
apps/api/app/schemas/events.py:168:    @field_validator("sponsor_tier", "business_name", mode="before")
apps/api/app/schemas/events.py:170:    def trim_sponsor_text(cls, value: Any) -> str | None:
apps/api/app/schemas/payments.py:7:from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
apps/api/app/schemas/payments.py:9:_ALLOWED_CHECKOUT_KINDS = {"donation", "sponsor", "membership"}
apps/api/app/schemas/payments.py:24:    donor_name: str = Field(default="", max_length=120)
```

## Flask / database introspection

```text
app_import=ok
instance_path=/home/elCUCO/futurefunded-main/instance

config/env signals:
SQLALCHEMY_DATABASE_URI=missing
DATABASE_URL=present:sqlite:////home/elCUCO/futurefunded-final/.data/futurefunded-dev.db
STRIPE_PUBLIC_KEY=missing
STRIPE_SECRET_KEY=missing
STRIPE_WEBHOOK_SECRET=missing
PAYPAL_CLIENT_ID=missing
PAYPAL_CLIENT_SECRET=missing
MAIL_SERVER=missing
MAIL_PORT=missing
MAIL_USERNAME=missing
MAIL_DEFAULT_SENDER=missing
MAIL_USE_TLS=missing
MAIL_USE_SSL=missing
SENDGRID_API_KEY=missing
RESEND_API_KEY=missing
POSTMARK_API_TOKEN=missing

url map money/dashboard routes:
campaign._ff_embedded_checkout_session_v1     POST         /<slug>/checkout/embedded-session
campaign.ff_embedded_checkout_session_status  GET          /<slug>/checkout/session-status
campaign._ff_embedded_checkout_session_v1     POST         /c/<slug>/checkout/embedded-session
campaign.ff_create_campaign_checkout_session  POST         /c/<slug>/checkout/session
campaign.ff_embedded_checkout_session_status  GET          /c/<slug>/checkout/session-status
campaign.ff_campaign_ledger_events            GET          /c/<slug>/ledger/events
campaign.ff_campaign_ledger_export_csv        GET          /c/<slug>/ledger/export.csv
campaign.ff_create_offline_donation           POST         /c/<slug>/ledger/offline-donation
campaign.ff_campaign_ledger_summary           GET          /c/<slug>/ledger/summary
campaign.ff_campaign_payment_config           GET          /c/<slug>/payments/config
campaign.ff_create_paypal_order               POST         /c/<slug>/paypal/orders
campaign.ff_capture_paypal_order              POST         /c/<slug>/paypal/orders/<order_id>/capture
campaign.ff_stripe_webhook                    POST         /c/stripe/webhook
platform.platform_operator_dashboard          GET          /dashboard
platform.platform_operator_login_form         GET          /login
platform.platform_operator_login_submit       POST         /login
platform.platform_operator_logout             GET,POST     /logout
platform.dashboard                            GET          /platform/dashboard
platform.dashboard                            GET          /platform/dashboard/
platform.platform_operator_login_form         GET          /platform/login
platform.platform_operator_login_submit       POST         /platform/login
platform.platform_operator_logout             GET,POST     /platform/logout
sponsors.sponsors_index                       GET          /sponsors
sponsors.sponsors_index                       GET          /sponsors/
sponsors.sponsor_lead                         POST         /sponsors/lead
sponsors.sponsor_lead                         POST         /sponsors/lead/
sponsors.sponsor_lead_stage_update            POST         /sponsors/lead/<lead_id>/stage
sponsors.sponsor_lead_stage_update            POST         /sponsors/lead/<lead_id>/stage/

SQLAlchemy tables:
sqlalchemy_db=not_found
```

## Required production readiness checklist

| Area | Required before real launch | Status to confirm |
|---|---|---|
| Database | Managed production DB, not local demo SQLite | Needs confirmation |
| Donation records | Completed Stripe/PayPal gifts stored in durable table | Needs proof |
| Webhooks | Stripe webhook validates signature and writes payment status | Needs proof |
| Emails | Donor receipt and organizer alert configured | Needs proof |
| Dashboard ledger | Dashboard reads real stored gifts/sponsors/offline donations | Needs proof |
| Export | CSV export pulls real stored records | Needs proof |
| Secrets | Live/test keys separated and not committed | Needs confirmation |
| Backups | Production DB backup/restore plan exists | Needs confirmation |

## Interpretation

If Stripe/PayPal keys, webhook secret, mail provider config, and durable money tables show missing, the product is demo-ready but not yet real-money-operations-ready.

## Environment example

Use `docs/release/futurefunded-money-env.example` as the safe example file. Do not commit real `.env` files or real secrets.
