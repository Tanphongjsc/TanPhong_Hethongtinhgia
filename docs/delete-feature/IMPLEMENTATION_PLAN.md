# Delete Functionality Implementation Plan

> For agentic workers: use superpowers:executing-plans in this session. User explicitly requested implementation without another analysis/approval stop; preserve the supplied spec and agreed proportional policy.

**Goal:** Enable safe deletion for existing editable records, preserving locked results and current calculations.
**Architecture:** An explicit entity registry, deletion-only inspection/service boundary and shared confirmation endpoint/component. Existing child-remove URLs keep their responses. Reuse internal compatibility locking to serialize deletion with symbolic-reference writers; no identity workflow.
**Tech Stack:** Django ORM, PostgreSQL, Django Templates, HTMX, Alpine, existing Tailwind/Lucide.
**Spec:** user attachment 97b6e677-f31a-42b8-85de-36ec88fe3051/Pasted text.txt and preceding approved deletion-policy discussion.

## Global Constraints
- Correct repository: D:/TANPHONGJSC/HeThongTinhGiaThanh/TanPhong_Hethongtinhgia.
- No business model/schema/migration, Auth, Organization UI, financial engine, Golden, or existing POST payload changes.
- Only localhost isolated test_costing_slice; never delete live Supabase records.
- POST + CSRF + signed record-specific confirmation; GET is read-only.
- No bulk deletion. No automatic deletion of other business entities.
- Full snapshots can produce warnings rather than blanket historical bans; unknown required evidence blocks.
- Current CostingRun records remain protected until replay-key retention can be supported safely without schema changes. Calculated scenarios remain protected; DRAFT scenarios without successful output may be deleted.

## Review Focus
- Races between deletion and symbolic definition creation/calculation: shared lock and database FK enforcement; transaction test.
- Historical snapshots with complete versus malformed/partial evidence: warning versus blocker; persisted-history tests.
- Stale/replayed confirmation or cross-record tokens: no mutation; HTTP tests.
- Deleting draft versions removes only explicitly owned children and retains shared tests/masters; integration tests.
- HTMX cancellation, errors and mobile focus: real Chromium checks.

## Files and Interfaces
- Create apps/master_data/deletion_registry.py: explicit supported entities, UI names, route/context mapping, owned-child policy.
- Create apps/master_data/deletion.py: get_record(workspace, resource, identifier), inspect_deletion(record), delete_record(workspace, resource, identifier, token), private deletion-only serialization. Real FK queries; logical reference checks and signed state confirmation.
- Create apps/master_data/deletion_history.py: typed snapshot evidence inspection; no calculations or reinterpretation of arbitrary JSON text.
- Create apps/master_data/deletion_views.py and templatetags/deletion_tags.py: confirmation GET/POST and detail action composition.
- Create templates/master_data/delete_confirm.html, partials/delete_confirm_content.html and components/delete_action.html; reuse modal, focus, errors, toast and redirect patterns.
- Modify master_data/urls.py, layouts/page_header.html, five version-detail partials, packaging assignment rows; preserve other actions.
- Modify four existing child-remove services only for deletion guards. All additional locking is inside the new deletion transaction; do not decorate or modify other writers/calculation services.
- Test fixtures may add missing mapped tables ONLY inside the isolated unmanaged-model test runner.

## Task 1: Backend and HTTP safety
- [x] Write failing HTTP tests for independent deletion, parent dependency, immutable status, CSRF/GET, missing/stale/wrong token and duplicate submission.
- [x] Run tests; record expected 404 failures before feature exists.
- [x] Implement explicit policies and transaction boundary; test a real FK violation/rollback, no test-only production flags.
- [x] Verify green targeted tests.

## Task 2: Indirect dependencies and owned draft data
- [x] Add failing tests for exact code references, ALLOCATION references, conversion dependencies, snapshot warnings/unknown blockers, draft-only version children, shared formula tests.
- [x] Implement typed checks, deletion-only locking and guarded existing child remove services.
- [x] Test locked history and unchanged Golden Costing/Pricing.

## Task 3: User interface
- [x] Add failing render/browser tests for action discovery, signed confirmation, cancel, submit-once, rejection and responsive navigation.
- [x] Integrate shared dialog with normal-page fallback and redirect after detail deletion; assignment rows use partial-refresh behavior.
- [x] Build CSS and run targeted browser tests.

## Task 4: Verification and documentation
- [x] Run Django check, complete suite, selected browser regressions and legacy UI contract audit; compare pre-existing failures honestly.
- [x] Confirm engine/model/Golden files unchanged and no live DML or schema migration.
- [x] Complete DELETE_COVERAGE_MATRIX.md, DELETE_POLICY.md and DELETE_IMPLEMENTATION_REPORT.md with observed counts, URLs, limitations and commands.
- [x] Self-review and fresh code review; fix findings, rerun affected checks.

## Execution ledger
- Baseline 799 tests, 35 opt-in skipped; existing 1 frozen-UI-contract failure + 2 Windows subprocess-stderr test errors. Stored artifacts/delete-feature/baseline-tests.log.
- Ruling: preserve current folder and dirty app.css; no worktree relocation or commits without request, because user explicitly designated this project and requested direct implementation.
- Ruling: keep complete saved runs (including failed requests) until replay protection is retained; this is documented per spec's allowed schema-limited scopes, not a new Run state.
- Ruling: hidden core mappings are protected as dependencies; no new CRUD UI for unimplemented RuleTable/period/identity features.
- Review correction: broad writer decorators were rejected by automatic approval review before execution; the approved implementation locks only inside deletion and adds four child-remove guards. No writer/calculation service decorators were applied.
- Final verification: 47 deletion server tests and 10 browser/Golden regressions passed; full suite 849 tests, 810 passed/38 skipped/1 historical UI-baseline failure. Real immediate/deferred FK rollback cases are included in the targeted and final full suite. See DELETE_IMPLEMENTATION_REPORT.md for logs and limitations.
