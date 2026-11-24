# ADR-003: Lint and CI standardization

## Status

Accepted (2026-11-21).

## Context

The 10 Frappe apps of the group are being prepared for unification and for the v15 -> v16/v17 migration. Before that,
the apps diverged in lint and CI (Python version, ruff version and rules, ignores, pre-commit excludes, use of
prettier/eslint). This ADR records the standardization applied to this repository (`integracoes_customizadas`).

## Decision

1. **Python: minimum 3.11 kept** (`target-version = "py311"`, `requires-python = ">=3.11"`, `linter.yml` on 3.11),
   due to a production constraint: the production/staging images are confirmed on Python 3.12. **Migration target for
   Frappe v16: `>=3.13`** (`target-version = "py313"`, `requires-python = ">=3.13"`, consistent `linter.yml` and
   `ci.yml`), to be done at migration time. `ci.yml` now runs Python 3.12 (previously 3.14) to reflect production:
   3.14 is incompatible with Frappe v15 (freezegun breaks at test collection with
   `AttributeError: module 'uuid' has no attribute '_load_system_functions'`).
2. **ruff pinned to v0.16.10** via `ruff-pre-commit`, rules `F,E,W,I,UP,B,RUF` and CLM's `ignore` list, with no
   additional `UP` ignores (see decision 13).
3. **pyupgrade covered by ruff's `UP` rule**, with no separate hook.
4. **F401 is NOT ignored**: dead imports were removed; re-exports/side-effect imports are kept with
   `# noqa: F401  # <reason>`. User-visible strings with an ambiguous unicode character (e.g. an en dash) get
   `# noqa: RUF001` instead of changing the text.
5. **prettier 2.7.1 and eslint 8.44.0 kept**: the upgrade was postponed so as not to mix with the standardization;
   review when preparing for v16/v17.
6. **Pre-commit excludes are always paths of the repository itself**, dead entries removed, without widening the
   ignored scope.
7. **ESLint globals declared in `.eslintrc` with minimal scope**: `busca_cnpj` as `"readonly"` (namespace of the
   dependent app `busca_cnpj`, used in `processo_judicial.js`). No `overrides` were needed (there are no
   Frappe-injected variables such as `root_element`).
8. **JS files with Jinja excluded by exact path**: none. The only JS with Jinja syntax
   (`juridico/report/relacao_de_processos/relacao_de_processos.js`) keeps the Jinja inside a template string and
   passes prettier and eslint normally.
9. **JS formatted by prettier in a style-only commit**: 6 `.js` files.
10. **pip-audit runs only in CI and audits only `pyproject`**; the `erpnext`/`hrms` dependencies are commented out, so
    coverage is small (see Open items).
11. **commitlint kept** and `pre-commit install` documented in `AGENTS.md`.
12. **No tag and no `__version__` change** in this standardization.
13. **Exams SQL queries: the `main` f-string is kept, with `# nosemgrep: frappe-sql-format-injection`.** The three
    queries (`candidatos_por_etapa`, `candidatos_por_status`, `comparativo_entre_editais`) stay as in `main` (f-string,
    which `ruff --fix` UP032 produced). It was verified that `conditions` is built only from constant fragments
    (`" AND e.name = %(edital)s"` etc.) and that all values go through named parameters, without interpolating user
    input; the finding is therefore a false positive and is suppressed, with a justification comment, on the line
    immediately before the call. Discarded alternative: going back to `.format(conditions=...)` and restoring the
    `UP030/031/032/037/040` ignores. The premise that `.format` would avoid semgrep was false: the rule detects
    `.format()` and f-strings alike, and the reversion would only increase the diff against `main` and weaken ruff.
    The extra `UP` ignores were therefore **not** restored.
14. **`get_open_count` (`juridico/dashboard.py`) with `items: str | list | None = None`**, required by the
    `missing-argument-type-hint` rule. Validated against `frappe.utils.typing_validations` (v15): `None`, JSON string
    and list pass; `dict` and `int` are rejected.
15. **CI: stubs of nonexistent DocTypes in the test setup.** The `Employee` and `Designation` Custom Fields in
    `fixtures/custom_field.json` point to the DocTypes `Municipios` (`Employee-custom_naturalidade_cidade`), `CBO`
    (`Designation-custom_cbo`) and `Dependentes` (`Employee-custom_dependentes`), which do not exist in any app of the
    group (probably created by hand in production). Without them, creating the hrms test records fails with
    `WrongOptionsDoctypeLinkError`. The "Run Tests" step of `ci.yml` calls
    `integracoes_customizadas.tests.site_setup.criar_doctypes_stub` (idempotent, no hook, test only; stubs in the
    `Custom` module, which does not belong to the app). The same script creates the Custom Field
    `Item.custom_código_bionexo`, used by `importacao_bionexo.py` and also absent from fixtures/patches. **A clean
    install of the app depends on those DocTypes, which are not in the app**: separate product task (create them in
    the app or remove/condition the fields).

## Consequences

- Ruff, prettier and eslint run identically locally (pre-commit) and in CI; style divergences stop appearing in
  reviews.
- Dead imports no longer go unnoticed; re-exports must justify the `noqa`.
- Batch formatting produced style-only diffs, isolated in their own commits (`style:`) so as not to pollute
  `git blame` of functional changes.
- Prettier and eslint stay on old versions until the preparation for v16/v17.

## State of this repository

| Item | State |
| --- | --- |
| F401 (commit `fix: corrigir erros do ruff check`) | 2 dead names removed (`now_datetime`, `today`); 1 re-export kept with `# noqa: F401  # compat` (`bionexo_export.py`) |
| RUF001 | 2 occurrences with `# noqa: RUF001` (`juridico/agenda_alerts.py`) |
| Pre-commit excludes changed | None (prettier and eslint keep the original excludes) |
| ESLint | `busca_cnpj` declared `readonly`; no real undefined-variable bug found |
| prettier | 6 `.js` files reformatted; no non-JS file changed |
| `pre-commit run --all-files` (without commitlint) | All hooks pass |

## Open items

- Upgrade prettier (2.7.1) and eslint (8.44.0) when preparing for v16/v17.
- Migrate the Python target to `>=3.13` at the v16 migration (production/staging currently on Python 3.12).
- Extend pip-audit to cover the `erpnext`/`hrms` dependencies (currently commented out in `pyproject`).
