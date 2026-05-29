# FutureFunded Product Spine Patch Gate

Run before committing UI, CSS, template, JS, or route changes:

```bash
scripts/dev/ff-spine-gate.sh

The gate checks:

repo shape
git state and diff capture
CSS brace integrity
Flask route health
linked CSS per route
critical campaign hooks
horizontal overflow
mobile/tablet/desktop screenshots

Generated output is ignored under:

audit_outputs/spine-gate/

Do not commit UI changes unless screenshots look correct.
