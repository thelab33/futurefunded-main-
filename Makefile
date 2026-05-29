SHELL := /bin/bash

VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
PIP ?= $(VENV)/bin/pip
NPM ?= npm

PYTHONPATH_WEB := apps/web
PYTHONPATH_API := apps/api
FLASK_APP_PATH := apps/web/wsgi.py

export PYTHONPATH_WEB
export PYTHONPATH_API
export FLASK_APP_PATH

.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "FutureFunded operator commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install"
	@echo ""
	@echo "Local servers:"
	@echo "  make web"
	@echo "  make api"
	@echo "  make serve-prod-local"
	@echo ""
	@echo "Quality:"
	@echo "  make lint"
	@echo "  make lint-fix"
	@echo "  make format"
	@echo "  make test"
	@echo "  make qa"
	@echo ""
	@echo "Launch:"
	@echo "  make readiness"
	@echo "  make deploy-final"
	@echo "  make launch-audit URL=https://example.com"

.PHONY: install
install:
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e ".[dev]"
	$(NPM) install

.PHONY: web
web:
	PYTHONPATH=$(PYTHONPATH_WEB) FLASK_APP=$(FLASK_APP_PATH) $(PYTHON) -m flask run --host 127.0.0.1 --port 5000

.PHONY: api
api:
	PYTHONPATH=$(PYTHONPATH_API) $(PYTHON) -m uvicorn asgi:app --app-dir apps/api --host 127.0.0.1 --port 8000 --reload

.PHONY: lint
lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m black --check .
	$(NPM) run lint
	$(NPM) run format:check

.PHONY: lint-fix
lint-fix:
	$(PYTHON) -m ruff check . --fix
	$(PYTHON) -m black .
	$(NPM) run lint:css:fix
	$(NPM) run format

.PHONY: format
format:
	$(PYTHON) -m black .
	$(NPM) run format

.PHONY: check-js
check-js:
	@find apps/web/app/static/js -name '*.js' -print0 | xargs -0 -r node --check

.PHONY: test
test:
	$(PYTHON) -m pytest -q || [ $$? -eq 5 ]
	$(NPM) run test:js

.PHONY: qa
qa:
	$(MAKE) lint
	$(MAKE) test
	$(NPM) run qa:frontend

.PHONY: qa-strict
qa-strict:
	$(MAKE) lint
	$(MAKE) test
	$(NPM) run qa:handoff:strict

.PHONY: ui-smoke
ui-smoke:
	@bash scripts/smoke_ui_contract.sh

.PHONY: kill-5000
kill-5000:
	@fuser -k 5000/tcp 2>/dev/null || true
	@pkill -f 'gunicorn.*5000' 2>/dev/null || true

.PHONY: kill-8000
kill-8000:
	@fuser -k 8000/tcp 2>/dev/null || true
	@pkill -f 'uvicorn.*8000' 2>/dev/null || true

.PHONY: kill-local
kill-local: kill-5000 kill-8000

.PHONY: serve-prod-local
serve-prod-local:
	@bash scripts/serve_local_prod.sh

.PHONY: smoke-live
smoke-live:
	@bash scripts/smoke_ui_contract.sh
	@curl -fsS http://127.0.0.1:5000/platform/ | rg 'ff\.tokens\.css|ff\.base\.css|ff\.pages\.css|site\.webmanifest'
	@curl -fsS http://127.0.0.1:5000/c/connect-atx-elite | rg 'ff\.tokens\.css|ff\.base\.css|ff\.pages\.css|site\.webmanifest'

.PHONY: readiness
readiness:
	@bash scripts/smoke_ui_contract.sh
	@bash scripts/check_prod_headers.sh
	@echo "readiness checks passed"

.PHONY: deploy-audit
deploy-audit:
	@bash scripts/check_no_localhost_prod.sh

.PHONY: readiness-local
readiness-local:
	@bash scripts/smoke_ui_contract.sh
	@bash scripts/check_prod_headers.sh
	@echo "local readiness checks passed"

.PHONY: readiness-deploy
readiness-deploy:
	@test -f .env.production.example
	@test -f DEPLOY_CHECKLIST.md
	@bash scripts/check_no_localhost_prod.sh
	@echo "deploy readiness config checks passed"

.PHONY: deploy-env-check
deploy-env-check:
	@bash scripts/check_required_prod_env.sh .env.production

.PHONY: deploy-final
deploy-final:
	@test -f .env.production
	@bash scripts/check_required_prod_env.sh .env.production
	@bash scripts/check_no_localhost_prod.sh
	@echo "deploy-final checks passed"

.PHONY: deployed-header-audit
deployed-header-audit:
	@test -n "$(URL)"
	@bash scripts/check_deployed_headers.sh "$(URL)"

.PHONY: launch-audit
launch-audit:
	@test -n "$(URL)"
	@bash scripts/check_deployed_headers.sh "$(URL)"
	@echo "launch audit passed for $(URL)"

.PHONY: dns-check
dns-check:
	@test -n "$(DOMAIN)"
	@bash scripts/check_dns_ready.sh "$(DOMAIN)"

.PHONY: audit-templates
audit-templates:
	$(PYTHON) scripts/audit_template_contract.py
