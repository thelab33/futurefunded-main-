# Auth CSS Authority Split

Date: 2026-05-29T13:42:16-05:00

Result:
- Created apps/web/app/static/css/auth.css as the auth-suite visual authority.
- Login page now loads auth.css through its page_css block.
- Removed old merged login.css visual authority from ff.css when marker was found.
- Added ff.css auth handoff marker:
  - hoi-auth-css-handoff-v1
- Preserved login hooks:
  - data-ff-login-root
  - data-ff-login-form
  - data-ff-login-email
  - data-ff-login-password
  - data-ff-login-password-toggle
  - data-ff-login-submit
  - data-ff-login-js

Future auth suite prepared:
- /platform/login
- /platform/forgot-password
- /platform/reset-password
- /platform/invite
- /platform/mfa
- /platform/register

Reports:
- audit_outputs/auth-css-authority/20260529134210/reports/contract-proof.txt
- audit_outputs/auth-css-authority/20260529134210/reports/route-proof.txt
- audit_outputs/auth-css-authority/20260529134210/reports/rendered-auth-css-link.txt

Safety tag:
- safety-before-auth-css-authority-20260529134210
