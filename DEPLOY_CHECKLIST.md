# FutureFunded deploy checklist

## Secrets

- [ ] SECRET_KEY is set to a long random production secret
- [ ] WTF_CSRF_SECRET_KEY is set
- [ ] No ephemeral local secrets are used in real deploy

## URLs

- [ ] PUBLIC_BASE_URL uses the real HTTPS domain
- [ ] API_BASE_URL uses the real HTTPS API domain
- [ ] No localhost or 127.0.0.1 values remain in deploy config

## App mode

- [ ] FLASK_DEBUG=0
- [ ] FLASK_ENV=production
- [ ] ENV=production
- [ ] APP_ENV=production

## HTTP and proxy

- [ ] Gunicorn runs behind a TLS reverse proxy
- [ ] HTTPS is terminated at the proxy or load balancer
- [ ] Proxy forwards host and scheme correctly

## Security headers

- [ ] CSP present
- [ ] X-Content-Type-Options present
- [ ] X-Frame-Options present
- [ ] Referrer-Policy present
- [ ] Permissions-Policy present

## CSP follow-up

- [ ] Remove unsafe-inline from style-src if possible
- [ ] Remove unsafe-inline from script-src if possible
- [ ] Replace localhost connect-src entries with real production origins

## Static and templates

- [ ] /static/site.webmanifest returns 200
- [ ] Platform page loads ff.tokens.css, ff.base.css, ff.pages.css
- [ ] Campaign page loads ff.tokens.css, ff.base.css, ff.pages.css
- [ ] No inline style violations in live templates

## Final checks

- [ ] make deploy-audit passes
- [ ] make readiness-deploy passes
- [ ] Manual smoke on /platform/ passes
- [ ] Manual smoke on /c/connect-atx-elite passes
