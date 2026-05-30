# FutureFunded Clean Root Command Card

## Source of truth

    ~/futurefunded-main

## Archive/reference only

    ~/futurefunded-product-spine

## Daily start

    cd ~/futurefunded-main || exit 1
    source .venv/bin/activate
    ffserver restart

## Server status

    ffserver status

## Full proof

    npm run doctor

## Campaign URL

    http://127.0.0.1:5000/c/connect-atx-elite

## Platform URL

    http://127.0.0.1:5000/platform/

## Login URL

    http://127.0.0.1:5000/platform/login

## Onboarding URL

    http://127.0.0.1:5000/platform/onboarding

## Dashboard URL

    http://127.0.0.1:5000/platform/dashboard\?access_token\=dev-operator-20260529123018

## Rule

Do not patch or run launch commands from old repos.
