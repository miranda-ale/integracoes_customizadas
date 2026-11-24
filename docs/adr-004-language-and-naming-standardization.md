# ADR-004: Language and naming standardization (phase 1)

## Status

Accepted (2026-11-24). Phase 1 is partially implemented in this repository; see "Pending work".

## Context

The 10 Frappe apps of the group (`clm`, `rh_brasil`, `busca_cnpj`, `integracoes_customizadas`,
`assinatura_eletronica`, `pdf_ocr`, `pulse_gestor`, `pulse_finance`, `pulse_process`, `bhcl_site`) are being unified
and migrated from Frappe v15 to v16. Until now each app followed its own conventions: Portuguese documentation,
comments and identifiers, accented names of Reports, Workspaces and DocTypes, mixed publishers and licenses, and
`required_apps` in different formats. The target standard is
[`clm/docs/naming-conventions.md`](https://github.com/still-pulse/clm/blob/main/docs/naming-conventions.md) and
[`clm/docs/fixtures-and-migrations.md`](https://github.com/still-pulse/clm/blob/main/docs/fixtures-and-migrations.md)
(repository `clm`). Phase 1 covers only naming and language; renaming persisted business names (DocTypes, fieldnames,
roles, record names) is Phase 2. Lint and CI changes are covered by [ADR-003](adr-003-lint-and-ci-standardization.md).

## Decision

1. **English** for documentation, comments, docstrings, identifiers (functions, modules, variables, files) and commit
   messages. **pt-BR only** for user-facing labels and messages (`label`, `translations/`) and for persisted values.
2. **ASCII-only names** for Report, Print Format, Workspace and DocType (accents only in `label`/`title`).
3. Metadata: `app_publisher = "StillPulse Tecnologia LTDA"`, `app_license = "Proprietary"` with a proprietary
   `license.txt`, copyright headers "StillPulse Tecnologia LTDA and contributors", and no client brand in metadata.
4. `required_apps` as a list of `"org/repo@branch"` strings (`frappe/frappe@version-15`, `frappe/erpnext@version-15`,
   `frappe/hrms@version-15`, `still-pulse/<app>@main`).
5. New patches are `sNN_<action_in_snake_case>`; existing patches are never renamed or edited (the Patch Log
   identifies them by path). Renames of persisted records use idempotent `pre_model_sync` patches with
   `frappe.rename_doc`.
6. Cross-app imports are either declared in `required_apps` or guarded by `frappe.get_installed_apps()`; the map is in
   [dependencies.md](dependencies.md).

## What changed in this repository

**Metadata and documentation**

- Publisher, license, copyright headers and `required_apps` as above (`hooks.py`, `pyproject.toml`, `license.txt`).
- All Markdown translated to English; files renamed: `adr-001-leitura-minima-...` -> `adr-001-minimal-read-on-linked-doctypes`,
  `adr-002-qualidade-...` -> `adr-002-log-quality-and-readability`, `adr-003-padronizacao-de-lint-e-ci` ->
  `adr-003-lint-and-ci-standardization`, `datajud-qualidade-de-logs` -> `datajud-log-quality`, `fluxo-compras` ->
  `purchasing-flow`, `juridico-dashboard` -> `legal-dashboard`, `modulo_provas` -> `exams-module`. New
  `dependencies.md`; `AGENTS.md` and `CLAUDE.md` gained a "Language and naming" section.

**Module, file and asset renames** (imports, hooks, JS and docs updated)

| Old | New |
| --- | --- |
| `email_institucional.py` | `institutional_email.py` |
| `normalizacao/maiusculas.py`, `public/js/maiusculas.js` | `normalization/uppercase.py`, `public/js/uppercase.js` |
| `politicas/acesso_doctypes.py` | `policies/doctype_access.py` |
| `seed/variantes_modelos.py` | `seed/template_variants.py` |
| `juridico/agenda.py`, `indicadores.py`, `parte.py`, `relatorios.py` | `juridico/agenda_alerts.py`, `indicators.py`, `party.py`, `report_helpers.py` |
| `whatsapp/distribuidor.py` | `whatsapp/dispatcher.py` |
| package `compras/`, `public/js/compras_steps.js`, `public/css/compras_steps.css` | `procurement/`, `procurement_steps.js`, `procurement_steps.css` (JS namespace `procurement.steps`) |
| `juridico/custom_blocks/indicadores_juridico.{html,js}` | `legal_indicators.{html,js}` |
| tests `test_maiusculas_nomes`, `test_distribuidor`, `test_juridico_indicadores`, `test_politica_acesso`, `test_traducoes_compras`, `test_workspaces_compras`, `test_compras_process`, `test_regras_notificacao` | `test_uppercase_names`, `test_dispatcher`, `test_legal_indicators`, `test_access_policy`, `test_procurement_translations`, `test_procurement_workspaces`, `test_procurement_process`, `test_notification_rules` |

Folders and files with accents were renamed to ASCII (reports `relacao_de_processos` and `provisao_de_processos`,
workspace `juridico`, DocType folder `datajud_settings`). Missing `__init__.py` files were added. Two legacy patches
only had their import path updated (`maiusculas_nomes_existentes`, `semear_variantes_modelo_whatsapp`), with no logic
change.

**Patches** (both `[pre_model_sync]`, idempotent, safe to retry)

- `s01_rename_datajud_settings`: renames the Single DocType `Configurações DataJud` to `DataJud Settings` with
  `frappe.rename_doc("DocType", ...)`. Because `rename_doc` does not rekey the Single's stored values, it also updates
  `tabSingles.doctype` and `__Auth` (`doctype` and `name`, which hold the encrypted `api_key` and the circuit-breaker
  state), only when the new rows do not exist yet. If the new DocType already exists it moves the leftover values and
  deletes the old DocType. Does nothing once the old name is gone.
- `s02_rename_juridico_reports_and_workspace`: renames Reports `Relação de Processos` -> `Relacao de Processos`,
  `Provisão de Processos` -> `Provisao de Processos` and Workspace `Jurídico` -> `Juridico`. `rename_doc` rewrites the
  links; if both names already exist, the legacy record is deleted. Skips records that are gone.

**Name chosen for the DataJud Single**: `DataJud Settings`, without an app prefix, to stay consistent with its sibling
`DataJud Sync Log` and avoid a second rename: all DocTypes of this app are still unprefixed, and the prefix will be
applied uniformly in Phase 2 with a single patch set.

**Guards and dependencies**: `institutional_email.ja_institucional` and `whatsapp/modelos._para_html` check
`frappe.get_installed_apps()` before importing `clm` / `assinatura_eletronica`. The `busca_cnpj` English API
(`lookup_cnpj`, `confirm_cnpj_data`, `normalize_cnpj`, `format_cnpj`, `validate_tax_id`, `validate_cpf`) is used instead
of its deprecated Portuguese aliases, and `required_apps` points to `still-pulse/busca_cnpj@main`; the JS helper
`busca_cnpj.taxid` is already used behind `window.busca_cnpj?.taxid`.

## Compatibility

`whatsapp.conector`, `whatsapp.roteador` and `whatsapp.modelos`, their Portuguese function names and the
`whatsapp_contexto_extra` hook were deliberately **not renamed**, because other apps import them: `rh_brasil`
(`roteador.variar_ativo`/`escolher`, `modelos.contexto`/`_renderizar_texto`/`_ENV`, the hook), `assinatura_eletronica`
(`conector.*`, `roteador.*`) and `pulse_gestor` (`modelos.enviar_modelo`, `conector.normalizar_numero_br`). When they
are renamed, English modules must ship together with deprecated shims that re-export the old names (and wrappers for
the old keyword arguments), the same approach `busca_cnpj` used, and the consumers must migrate in coordinated PRs
before the shims are removed.

## Consequences and risks

- **The Frappe bench and the patches were NOT executed.** Only `ruff check`, `ruff format --check`, `compileall` and a
  script that resolves every `integracoes_customizadas.*` dotted path were run. Run `bench migrate` on a site with
  real data (staging) and `bench run-tests --app integracoes_customizadas` before merging.
- Verify after migrating: `DataJud Settings` keeps its API key and circuit state; the saved report filters still open;
  the `Juridico` Workspace shows the title "Jurídico" (the JSON sets `name` and `label` to `Juridico` and `title` to
  `Jurídico`; this relies on the v15 sidebar using `title`).
- Asset paths changed (`procurement_steps.*`, `uppercase.js`): clear the website/desk cache after deploy.
- Rollback: revert the PR; for sites that already ran s01/s02, a reverse `rename_doc` is needed (the patches do not
  provide it).

## Pending work

- **Phase 2 (persisted names, needs patches)**: every DocType without the app prefix; fieldnames in Portuguese; the
  role `Usuário Jurídico` and the Custom HTML Block `Relatórios` (accents in names); the Dashboard Chart
  `Processos por Situação` (accent in its name); Report/Print Format names in Portuguese ASCII; the modules `Juridico`
  and `Provas`; malformed DocType class/folder names such as `TipodeDeficiencia`.
- **Custom Fields**: 66 Custom Fields on `Employee` and `Designation` (`fixtures/custom_field.json`) do not follow
  `custom_integracoes_customizadas_<meaning>`, many with accents. 35 of them are duplicated in `rh_brasil`
  (`rh_brasil/fixtures/custom_field.json` on `main`). The owner must be `rh_brasil`; this repository must remove the
  duplicates in a coordinated PR with `rh_brasil`, which should guard its own use.
- **Comments, docstrings and internal identifiers** in Portuguese remain (about 11.7 thousand lines of Python and
  3 thousand of JS), including functions, variables, constants, test classes and `test_*` names. Recommended approach: an
  AST-based renamer (`ast`/LibCST) driven by an explicit old->new map, which only rewrites Name, argument and
  definition nodes, never strings, attributes that are fieldnames or keyword arguments of non-project callables;
  protect the parameters of `@frappe.whitelist` functions (called by JS), Jinja context keys of persisted
  WhatsApp templates (`seguro`, `data`, `funcionario.*`) and the functions listed under Compatibility; then translate
  comments and docstrings by extraction/review per file.
- The test setup stubs (`tests/site_setup.py`, see ADR-003 decision 15) depend on DocTypes that are not in any app.
