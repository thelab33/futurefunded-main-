#!/usr/bin/env node
/**
 * FutureFunded ff.css v1 authority check
 * Usage: node scripts/verify/ff_css_v1_authority_check.mjs http://127.0.0.1:5000 connect-atx-elite
 */
const base = (process.argv[2] || process.env.FF_BASE_URL || 'http://127.0.0.1:5000').replace(/\/$/, '');
const slug = process.argv[3] || process.env.FF_CAMPAIGN_SLUG || 'connect-atx-elite';
const pages = [
  [`${base}/c/${encodeURIComponent(slug)}`, 'Campaign'],
  [`${base}/platform/`, 'Platform'],
  [`${base}/platform/onboarding`, 'Onboarding'],
  [`${base}/platform/login`, 'Login'],
];
const results = [];
function record(ok, label, detail = '') {
  results.push({ ok, label, detail });
  console.log(`${ok ? 'PASS' : 'CHECK'} ${label}${detail ? ` — ${detail}` : ''}`);
}
async function text(url) {
  const res = await fetch(url, { headers: { Accept: 'text/html' } });
  return { res, body: await res.text() };
}
console.log('\nFutureFunded ff.css v1 authority check');
for (const [url, label] of pages) {
  const { res, body } = await text(url);
  record(res.ok || res.status === 403, `${label} responds`, `status=${res.status}`);
  const ffCss = (body.match(/\/static\/css\/ff\.css/g) || []).length;
  record(ffCss >= 1, `${label} loads ff.css`, `count=${ffCss}`);
  if (label === 'Campaign') {
    record(!body.includes('ff.cinematic.css'), 'Campaign does not load cinematic CSS');
    record(!body.includes('ff-cinematic.js'), 'Campaign does not load cinematic JS');
    record(body.includes('ff.css'), 'Campaign loads global ff.css foundation');
record(body.includes('campaign.css'), 'Campaign loads campaign.css authority');
record(body.includes('data-ff-campaign-css-authority'), 'Campaign CSS authority contract is present');
record(body.includes('data-ff-checkout-css-contract'), 'Checkout CSS contract is owned by campaign.css');
record(!body.includes('ff.checkout.css') && !body.includes('ff-checkout-csp.css'), 'Legacy checkout CSS files are not linked');
    record(body.includes('ff-campaign.js'), 'Campaign loads campaign JS');
    record(body.includes('data-ff-open-checkout'), 'Campaign has checkout trigger contract');
  }
}
const failed = results.filter((r) => !r.ok);
console.log(`\nSummary: ${results.length - failed.length}/${results.length} passed`);
if (failed.length) process.exit(1);
