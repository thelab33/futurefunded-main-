# Auth CSS Authority Commit

Date: 2026-05-29T13:42:19-05:00

Committed:
- apps/web/app/static/css/auth.css
- apps/web/app/static/css/ff.css
- apps/web/app/templates/platform/login.html

Result:
- Auth suite now has its own CSS authority.
- Login visual styling moved out of ff.css.
- ff.css retains shared foundation only.
- Login template loads auth.css after the shared site foundation.
