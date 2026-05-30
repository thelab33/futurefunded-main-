# FutureFunded Launch Commands

## Repo

    cd ~/futurefunded-main || exit 1
    source .venv/bin/activate 2>/dev/null || true

## Start local demo

    bash scripts/demo/ff-demo-start.sh

## Open demo URLs

    bash scripts/demo/ff-demo-open.sh

## Campaign money proof

    node scripts/campaign-payment-smoke.mjs

## Fast proof

    bash scripts/demo/ff-fast-proof-strict.sh

## Product doctor

    npm run doctor

## Route smoke

    for path in /healthz /platform/ /platform/onboarding /platform/login /c/connect-atx-elite; do
      curl -fsS -o /dev/null -w "%{http_code}  $path\n" "http://127.0.0.1:5000${path}"
    done

## Rule

Do not run random legacy scripts from old repos.
Use this file as the command authority.
