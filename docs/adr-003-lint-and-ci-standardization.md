# ADR-003: Lint and CI standardization

## Status

Accepted (2026-11-21).

## Context

The 10 Frappe apps of the group are being prepared for unification and for the v15 -> v16/v17 migration. Before that,
the apps diverged in lint and CI (Python version, ruff version and rules, ignores, pre-commit excludes, use of
prettier/eslint). This ADR records the standardization applied to this repository (`integracoes_customizadas`).

## Decision

1. **Python 3.11** in CI, `target-version = "py311"` and `requires-python = ">=3.11"` (target to be reviewed for v16).
2. **ruff pinned to v0.16.10** via `ruff-pre-commit`, rules `F,E,W,I,UP,B,RUF` and an `ignore` list identical to CLM's.
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
| RUF001 | 2 occurrences with `# noqa: RUF001` (`juridico/agenda.py`) |
| Pre-commit excludes changed | None (prettier and eslint keep the original excludes) |
| ESLint | `busca_cnpj` declared `readonly`; no real undefined-variable bug found |
| prettier | 6 `.js` files reformatted; no non-JS file changed |
| `pre-commit run --all-files` (without commitlint) | All hooks pass |

## Open items

- Upgrade prettier (2.7.1) and eslint (8.44.0) when preparing for v16/v17.
- Review the Python target (3.11) for v16.
- Extend pip-audit to cover the `erpnext`/`hrms` dependencies (currently commented out in `pyproject`).
