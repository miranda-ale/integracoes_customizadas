# ADR-005 — Phase 2, wave 2: names of Reports, Print Formats, Charts, Cards, Dashboard, Workspaces and the Reports block

Status: proposed (merge needs L5).

## Decision

English names with the domain prefix `Integ`, ASCII only; the pt-BR labels come from `translations/pt-BR.csv` (new file).

| Kind | Old | New |
|---|---|---|
| Report | Aging de Processos | Integ Legal Cases Aging |
| Report | Candidatos por Etapa | Integ Candidates by Stage |
| Report | Candidatos por Status | Integ Candidates by Status |
| Report | Comparativo entre Editais | Integ Notice Comparison |
| Report | Mapa de Precos RFQ | Integ RFQ Price Map |
| Report | Passivo de Processos | Integ Legal Cases Liability |
| Report | Pedidos a Receber | Integ Orders to Receive |
| Report | Processos por Colaborador | Integ Legal Cases by Employee |
| Report | Provisao de Processos | Integ Legal Cases Provision |
| Report | Recebidos a Faturar | Integ Received Not Invoiced |
| Report | Relacao de Processos | Integ Legal Cases List |
| Print Format | Gabarito | Integ Exam Answer Key |
| Print Format | Minuta Edital | Integ Notice Draft |
| Print Format | Prova Completa | Integ Full Exam |
| Dashboard Chart | Assuntos Judiciais mais Frequentes | Integ Top Legal Subjects |
| Dashboard Chart | Processos por Fase | Integ Legal Cases by Phase |
| Dashboard Chart | Processos por Localidade IBGE | Integ Legal Cases by IBGE Location |
| Dashboard Chart | Processos por Risco | Integ Legal Cases by Risk |
| Dashboard Chart | Processos por Situação | Integ Legal Cases by Status |
| Dashboard Chart | Processos por Tribunal | Integ Legal Cases by Court |
| Number Card | Processos Encerrados | Integ Closed Legal Cases |
| Number Card | Processos em Andamento | Integ Ongoing Legal Cases |
| Number Card | Total de Processos Judiciais | Integ Total Legal Cases |
| Dashboard | Processos Judiciais | Integ Legal Cases |
| Workspace | Juridico | Integ Legal |
| Workspace | Provas | Integ Exams |
| Workspace | Integracoes | Integ Integrations |
| Custom HTML Block | Relatórios | Integ Reports |

Patch `integracoes_customizadas.patches.s03_rename_reports_print_formats_cards_and_workspaces` (`[pre_model_sync]`, idempotent)
renames with `frappe.rename_doc`, matching the old name exactly (the collation ignores accents and case), and replaces the
Custom HTML Block name inside the `content` of every Workspace (a JSON string that `rename_doc` does not rewrite). The standard
folders and files of Reports, Print Formats and the Juridico Workspace follow `scrub(name)`.

Not renamed: the Module Defs `Juridico`, `Provas` and `Integracoes Customizadas` (a module name is a different contract) and
card labels such as `Relatórios` in Workspaces. In `procurement/workspaces.py` only the `link_to` of a shortcut changes; the
visible label of the shortcut stays, so the idempotent organizer does not create duplicates.

## Compatibility

`rh_brasil`, `clm` and `pulse_gestor` do not call these names (checked); `pulse_mobile` neither. Saved Reports, Workflows,
Server Scripts, Notification templates, bookmarks and hand-made Workspaces (their `content` may cite the Number Cards or Charts
by name) outside the repository are not rewritten: check them on staging. Report URLs change.

Patch `s02` (accented Juridico names to ASCII, before model sync) uses an exact-name check: `frappe.db.exists` ignores accents,
so it would delete the legacy Report instead of renaming it (found by L3). The check compares the names returned by
`frappe.get_all` exactly, as `s03` does.

## Verification (faithful baseline: production code migrated to `develop` plus this change)

- [x] L0 ruff check/format, compileall, JSON parse.
- [x] L3 23 objects present on the baseline were renamed (old gone, new present); the 5 that production names with accents
  (`Provisão de Processos`, `Relação de Processos`, Workspace `Jurídico`...) go through s02 and then s03; Has Role of the Reports
  preserved (32 rows); no Workspace or Dashboard row still points to an old name. The Juridico Workspace loses its three Number
  Cards on this upgrade: that is the existing `ensure_juridico_workspace` behaviour of `develop` (the indicators moved to the HTML
  block), not part of this change.
- [x] L4 second migrate identical; restore of the baseline backup identical to "before".
- [ ] L5 staging: **not executed**.
