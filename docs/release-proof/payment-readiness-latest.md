# FutureFunded Payment Readiness Gate

**Status:** PASS ✅
**Checked:** 2026-05-26T12:09:10-0500

## Summary

- Checks: 30
- Errors: 0
- Warnings: 1
- Campaign slug: `connect-atx-elite`

## Errors

- None

## Warnings

- no Stripe publishable key detected; acceptable only if checkout is disabled or configured elsewhere

## Checks

- ✅ **Flask app import**
- ✅ **environment payment mode snapshot**
- ✅ **campaign HTML secret leak scan**
- ✅ **campaign payment hooks**
- ✅ **payments config secret leak scan**
- ⚠️ **payments config public key**
- ✅ **checkout bad payload secret scan {}**
- ✅ **checkout rejects malformed payloads**
- ✅ **checkout bad payload secret scan {'amount': -1}**
- ✅ **checkout rejects malformed payloads**
- ✅ **checkout bad payload secret scan {'amount': 'not-money'}**
- ✅ **checkout rejects malformed payloads**
- ✅ **checkout bad payload secret scan {'amount': 0}**
- ✅ **checkout rejects malformed payloads**
- ✅ **checkout bad payload secret scan {'amount': 25, 'frequency': 'once', 'source': 'payment_readiness_gate'}**
- ✅ **checkout rejects malformed payloads**
- ✅ **checkout valid payload secret scan {'amount_cents': 2500, 'frequency': 'once', 'source': 'payment_readiness_gate'}**
- ✅ **checkout valid payload safe response**
- ✅ **webhook secret leak scan /c/stripe/webhook**
- ✅ **webhook invalid signature rejection**
- ✅ **ledger secret leak scan /c/connect-atx-elite/ledger/summary**
- ✅ **ledger route health**
- ✅ **ledger secret leak scan /c/connect-atx-elite/ledger/events**
- ✅ **ledger route health**
- ✅ **protected route secret leak scan /platform/dashboard**
- ✅ **operator protected route**
- ✅ **protected route secret leak scan /c/connect-atx-elite/ledger/export**
- ✅ **operator protected route**
- ✅ **protected route secret leak scan /c/connect-atx-elite/offline-donation**
- ✅ **operator protected route**
