# integracoes_customizadas

The rest of the repository instructions are in `CLAUDE.md`. Version rule:

- **A `feature/*` branch uses the `main` major + 1** (in force since 2026-11-01). Minor and patch run normally inside
  it: with `main` at `vX.Y.Z`, the feature starts at `v(X+1).0.0` and continues `v(X+1).0.1`, `v(X+1).1.0`... while on
  the branch. If `main` bumps its major, the feature bumps with it. Check the `main` version
  (`git show main:integracoes_customizadas/__init__.py`) and `git tag` before tagging, and never reuse an existing
  number.

## Lint and pre-commit

- Run `pre-commit install` once after cloning the repository.
- CI (`.github/workflows/linter.yml`) runs pre-commit, semgrep and pip-audit.
- Lint and CI standardization decisions: [docs/adr-003-lint-and-ci-standardization.md](docs/adr-003-lint-and-ci-standardization.md).

## Language and naming

Source of truth: [`clm/docs/naming-conventions.md`](https://github.com/still-pulse/clm/blob/main/docs/naming-conventions.md)
and [`clm/docs/fixtures-and-migrations.md`](https://github.com/still-pulse/clm/blob/main/docs/fixtures-and-migrations.md).

- Identifiers (functions, modules, variables, files), comments, docstrings, documentation and commit messages are
  written in **English** (snake_case; classes PascalCase). User-facing labels and messages stay pt-BR and go through
  `translations/`.
- New DocTypes and roles carry the app prefix; Reports, Print Formats and Workspaces have **ASCII-only** names
  (accents only in `label`).
- Custom Fields on `Employee`/`Designation` use `custom_integracoes_customizadas_<meaning>`.
- New patches are `sNN_<action_in_snake_case>` in `integracoes_customizadas/patches/` (next free number; existing
  patches are never renamed or edited) and are registered in `patches.txt` (`[pre_model_sync]` for renames).
- Renames of persisted names (DocTypes, fieldnames, roles, record names) need their own idempotent patch.
- Cross-app imports are declared in `required_apps` or guarded; see [docs/dependencies.md](docs/dependencies.md).
