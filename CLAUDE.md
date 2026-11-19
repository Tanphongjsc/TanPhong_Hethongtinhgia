# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Django 5.2 costing and pricing app (Hệ thống tính giá thành) on PostgreSQL (Supabase in production, schema `costing`, `search_path=costing,public`). The server renders the frontend with Django templates, HTMX, Alpine.js and Tailwind v4. There is no SPA and no REST API. The UI text is Vietnamese, but business codes, identifiers, field names, POST keys and URLs stay in English and must not be renamed.

Runtime mode is **single company with no authentication** (`APP_MODE=single_company`). There is no login, no user session, no Supabase Auth and no organization UI. CSRF is still enforced. Toast messages use signed cookies (`CookieStorage`).

## Commands (Windows / PowerShell, venv in `env/`)

```powershell
.\env\Scripts\Activate.ps1
python -m pip install -r requirements.txt   # requirements-dev.txt adds playwright
npm ci; npm run build                       # build:vendor (copies htmx/alpine/lucide/fonts into static/vendor) + build:css
npm run dev:css                             # Tailwind watch; edit static/src/tailwind.css, never static/css/app.css (generated)
python manage.py check
python manage.py runserver                  # uses .env (DB + DJANGO_SECRET_KEY, DJANGO_DEBUG=True)
```

Tests need PostgreSQL 17 binaries (`C:\Program Files\PostgreSQL\17\bin`, or set `COSTING_PG_BIN`). The script creates or starts a throwaway cluster in `.test-postgres` on `127.0.0.1:55432`, runs the tests, then stops it:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1                                   # full suite
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 apps.bom.test_routing             # one module
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 apps.bom.test_routing.SomeTests.test_x
```

- Arguments pass through to `manage.py test`. `manage.py` forces `config.test_settings` for `test` and refuses any other settings module. The custom runner `apps.master_data.testing.CostingTestRunner` **rejects `--keepdb` and `--parallel`**.
- Browser (Playwright) tests are opt-in with `$env:COSTING_BROWSER_TESTS = "1"`. Install the browser first: `$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\artifacts\playwright"; python -m playwright install chromium`. Screenshots are written to `artifacts/screenshots/`.
- `$env:COSTING_HARDENING_BENCHMARK = "1"` enables the load benchmark, which writes `artifacts/hardening-performance.json`.
- Demo and golden regression against the `.env` DB (idempotent; does not create a company or change schema): `python manage.py seed_costing_demo`, `python manage.py verify_costing_demo --report artifacts/demo-verification.json`, `python manage.py verify_pricing_demo --report artifacts/pricing-scenario-golden.json`. Golden values: 583.000 VND per 10 boxes, 58.300 VND/box cost, and 89.972,41379310 VND/box price.
- UI regression scripts that need no DB: `python scripts/audit_ui_contract.py compare`, `python scripts/verify_ui_static.py`.

There is no linter or formatter configured.

## Database-first: the most important constraint

- **Every business model is in `apps/core/models.py` with `managed = False`.** The other apps' `models.py` files are empty. The production schema already exists and is managed outside Django. **Never create or run business migrations.** `manage.py` blocks `migrate`, `flush` and `makemigrations` under production settings.
- Tests can't migrate unmanaged tables, so `CostingTestRunner.setup_databases` builds them with `schema_editor.create_model`. It then adds hand-written CHECK constraints and PL/pgSQL triggers that mirror production, such as immutability of APPROVED/EFFECTIVE/RETIRED versions. That code is in `apps/master_data/testing.py` and chains into `install_*` helpers in `apps/bom/testing.py`, `apps/formula_engine/testing.py`, `apps/costing/testing.py`, `apps/costing/run_testing.py` and `apps/pricing/testing.py`. **If you touch a model or add one to a test, register its fixture, constraints and triggers there**, or the tests won't match real DB behavior.
- Company context comes only from `apps/master_data/company_context.py:get_default_organization` (one active org, or `DEFAULT_ORGANIZATION_ID`, otherwise a 503 ConfigurationError). Access policy lives in `apps/master_data/access.py:InternalAccess`. Audit actor fields are stored as NULL. Don't fake UUIDs.
- Money, rates and quantities are always `Decimal`, never float.

## App layout and layering

URL prefixes are set in `config/urls.py`: `master-data/`, `product/`, `bom/`, `formula-engine/`, `costing/`, `pricing/`. `/` redirects to the cost element list.

Each feature inside an app uses a file-prefix convention instead of a sub-app. For example, `apps/bom/` holds Recipe/BOM (unprefixed) plus `packaging_*`, `resource_*`, `routing_*` and `overhead_*`. Each prefix has its own `*_constants`, `*_forms`, `*_selectors`, `*_services`, `*_validators`, `*_views` and `*_urls`. The `*_urls` lists are concatenated into the app's `urls.py` under a single namespace (`bom:`). Costing (`run_*`) and pricing (`scenario_*`, `comparison_*`) follow the same pattern.

- **views**: parse the request and render full pages or HTMX partials (`templates/<app>/.../partials/`). No calculation logic.
- **selectors**: read queries. **services**: write use cases; multi-table writes run inside `transaction.atomic` with `select_for_update`. **validators**: business rules on top of the DB constraints.
- **presentation.py** modules map stored data to Vietnamese labels for display. They must not touch the ORM or call engines. Shared label mappings live in `apps/master_data/presentation.py`.
- Shared UI infrastructure lives in `apps/master_data`: middleware, error handlers (`errors.py`), sidebar (`navigation.py`, which only lists implemented destinations), the `workspace` context processor, templatetags (`ui_tags`, `deletion_tags`, `workspace_tags`) and `ui_helpers.py`.
- Deletion is centralized. `deletion_registry.SPECS` maps each deletable model to a `DeleteSpec`. `deletion.py` blocks a delete when there are FK references, code references, conversions in use, missing history evidence, or locked versions. `deletion_views.py` provides the shared POST+CSRF confirmation modal. Policy: `docs/delete-feature/DELETE_POLICY.md`.

## Versioned and effective-dated data

Recipe, Packaging, Routing, Formula and CostingScheme follow a header → version → lines pattern. Versions move through DRAFT/IN_REVIEW (editable), APPROVED, EFFECTIVE and RETIRED. The last three are immutable through DB triggers, so the only way to change them is to clone into a new DRAFT, and the clone is atomic. Activation endpoints revalidate before setting EFFECTIVE. Prices and rates (SupplierPrice, ResourceRate, FX, tax and channel fees) are effective-dated rows.

## Calculation pipeline

1. **Formula Engine** (`apps/formula_engine/`): a custom DSL with no `eval`/`exec`. It goes parser → AST (allow-listed nodes, canonical hash) → validator (type/unit) → dependency and cycle detection → an iterative Decimal evaluator with execution budgets (`limits.py`). Functions come from a developer-defined registry (`functions.py`).
2. **Costing Scheme** (`apps/costing/` config side): scheme, version and lines map CostElements to a FormulaVersion or a SYSTEM resolver code. It validates but never evaluates.
3. **Costing Run** (`apps/costing/engine/`): `runner.py` is the HTTP-independent pipeline. DB reads happen only in dated resolvers (`engine/resolvers/`: prices, uom, manufacturing, allocation, scheme), registered in `engine/registry.py` (MATERIAL_COST, PACKAGING_COST, RESOURCE_COST, RUN_QUANTITY, `ALLOCATION:<rule_code>`). Status moves DRAFT → CALCULATED → LOCKED, or to FAILED. A run stores lines, sources, a snapshot with hash, and a trace. **Historical runs are read-only and never re-resolve current data.** A rerun creates a new record. Missing or ambiguous sources raise `CostingError`; never default them to 0 or pick the newest record.
4. **Pricing** (`apps/pricing/`): channels, fee rules, tax rules and FX feed a Pricing Scenario. The scenario is computed by `pricing/engine/` (`solver.py`) from a saved, locked Costing Run. Scenario comparison only reads stored snapshots.

## Docs and precedence

`docs/00_AI_CONTEXT.md` is the required entry point. Its section 1 is a dated changelog of the current architecture decisions. Per-feature specs (`docs/COSTING_RUN.md`, `docs/FORMULA_ENGINE.md`, `docs/PRICING_SCENARIO.md`, `docs/RECIPE_BOM.md`, and others) describe the schema, scope and limits of each module. Read the one for the module you're changing, not the whole `docs/` folder.

When sources conflict, this is the order of precedence: source code and DB schema → the newest feature spec → `00_AI_CONTEXT.md` → `02_BUSINESS_DOMAIN.md` → `03_SYSTEM_ARCHITECTURE.md` → `04_ENGINEERING_GUIDE.md`. Any older doc content about HRM integration, Supabase Auth, multi-tenant membership or RBAC is **superseded**. Costing has no business or FK dependency on HRM.

## Deployment notes

- Settings modules: `config.settings` (dev; reads `.env` only when `APP_ENV=development`), `config.production` (whitenoise; never reads `.env`), `config.test_settings`.
- Render: `build.sh`, then `gunicorn -c config/gunicorn.py config.wsgi:application`, health check at `/health/` (`/ready/` also exists). Windows/portable: `python -m config.serve --check`, then `python -m config.serve` (waitress).
- Deployments never run `migrate`, `seed` or `runserver`. Runbooks: `docs/06_DEPLOYMENT_DEVOPS.md` and `docs/DEPLOYMENT_RENDER.md`.
