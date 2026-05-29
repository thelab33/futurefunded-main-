# FutureFunded Deploy Preview Runbook

## Milestone

Tag: v0.1.0-frontend-green  
Repo: https://github.com/thelab33/futurefunded-final  
Goal: deploy a real hosted preview of the five-page MVP frontend + Flask backend.

## Current Green Contract

Pages:

- /platform/
- /c/connect-atx-elite
- /platform/login
- /platform/dashboard
- /platform/onboarding

Expected CSS stacks:

- Homepage: ff.css + ff.homepage-flagship.css
- Campaign: ff.css + ff.ui-micropolish.css
- Login: ff.css + ff.operator-dashboard.css
- Dashboard: ff.css + ff.operator-dashboard.css
- Onboarding: ff.css + ff.operator-dashboard.css

QA command:
npm run qa:frontend
npm run test:functionality
npm run qa:handoff

Known acceptable warnings:

- homepage sponsor-oriented link warning
- dashboard export CSV download warning in local smoke context

## Deploy Provider

Recommended first deploy: Render Web Service.

## Render Web Service Settings

Build command:
pip install -r requirements.txt && npm ci

Start command:
TBD after confirming Flask entrypoint. Likely one of:
gunicorn wsgi:app
gunicorn app:app
gunicorn "apps.web.app:create_app()"

## Required Environment Variables

Core:

- FLASK_ENV=production
- FLASK_DEBUG=0
- SECRET_KEY
- DATABASE_URL
- PUBLIC_BASE_URL
- FF_PUBLIC_BASE_URL

Operator:

- FF_OPERATOR_ACCESS_TOKEN

Stripe:

- STRIPE_SECRET_KEY
- STRIPE_PUBLISHABLE_KEY
- STRIPE_WEBHOOK_SECRET

PayPal:

- PAYPAL_CLIENT_ID
- PAYPAL_CLIENT_SECRET
- PAYPAL_ENV=live

Mail, optional:

- MAIL_SERVER
- MAIL_PORT
- MAIL_USERNAME
- MAIL_PASSWORD
- MAIL_DEFAULT_SENDER

## Post-deploy QA

1. Open /platform/
2. Open /c/connect-atx-elite
3. Open /platform/login
4. Open /platform/dashboard?operator_token=<token>
5. Open /platform/onboarding
6. Confirm no page-level horizontal overflow
7. Confirm donate modal opens
8. Confirm sponsor modal opens
9. Confirm share/copy/QR work
10. Confirm dashboard ledger loads
