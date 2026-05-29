# FutureFunded Product Spine Patch Gate

Run before committing UI, CSS, template, JS, or route changes:

```bash
scripts/dev/ff-spine-gate.sh
What the gate checks
Repo shape
Git state and diff capture
CSS brace integrity
Flask route health
Linked CSS per route
Critical campaign hooks
Horizontal overflow
Mobile/tablet/desktop screenshots
Browser dependency setup

If the browser audit cannot find Playwright, run:

npm ci --include=dev
npx playwright install chromium

Generated output is ignored under:

audit_outputs/spine-gate/

Do not commit UI changes unless screenshots look correct.
