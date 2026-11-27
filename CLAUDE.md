# integracoes_customizadas

See `AGENTS.md` for the language and naming rules and the lint workflow.

## Dependencies

- `required_apps = ["frappe/frappe@version-15", "frappe/erpnext@version-15", "frappe/hrms@version-15",
  "still-pulse/rh_brasil@develop", "still-pulse/busca_cnpj@develop"]`: they are not independent. The Legal module and the
  Bionexo import use `busca_cnpj` (English API names); the Legal module uses `rh_brasil.documentos`.
- **Weak, undeclared** dependencies: `clm` (`email_layout`, institutional e-mail, only if installed) and
  `assinatura_eletronica` (`servicos.canais`, WhatsApp formatting). They are guarded: do not import without checking
  `frappe.get_installed_apps()`.
- Other apps call this app with guards (`rh_brasil`: rescission WhatsApp and variants; `pulse_gestor`;
  `assinatura_eletronica`), so the `whatsapp.conector`, `whatsapp.roteador` and `whatsapp.modelos` names must stay
  importable. Full map: [docs/dependencies.md](docs/dependencies.md).
- Patches in this app are named by subject (legacy) or `sNN_<action>` (new) and do not follow the app version.

## Version, tags and documentation

- `__version__` in `integracoes_customizadas/__init__.py` must match the tag (currently `4.1.0`). Check it and
  `git tag` before tagging.
- **A `feature/*` branch uses the `main` major + 1** (in force since 2026-11-01). Minor and patch run normally inside
  it: with `main` at `vX.Y.Z`, the feature starts at `v(X+1).0.0` and continues `v(X+1).0.1`, `v(X+1).1.0`... while on
  the branch. If `main` bumps its major, the feature bumps with it. Check the `main` version
  (`git show main:integracoes_customizadas/__init__.py`) and `git tag` before tagging, and never reuse an existing
  number.
- Tags outside the HEAD history (`git tag --no-merged HEAD`) are not part of the app; ignore `rc/*` tags in the
  CHANGELOG.
- `README.md` and `CHANGELOG.md` are maintained by hand, only with what is committed; update both together with
  behavior changes.
- Overview of the dependencies between apps: `../../CLAUDE.md`.

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

## Git tags in cloud agent sessions

Agents running in a Claude Code cloud session cannot push git tags: the egress proxy answers `HTTP 403` (verified
2026-11-26; branch pushes work). It is a policy denial: do not retry or route around it. Commit and push the branch,
update `__version__` only when the task asks, and report once that the tag is pending. A human creates the tag
(`git tag vX.Y.Z && git push origin vX.Y.Z` from a normal machine, or a GitHub release). Details:
`pulse_platform/docs/handoff-dev-data.md`.
