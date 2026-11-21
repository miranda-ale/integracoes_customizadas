# Legal dashboard

Workspace `Juridico` (label "Jurídico"): `Juridico Indicadores` panel (Custom HTML Block, same pattern as
HR/SESMT/CLM) fed by `integracoes_customizadas.juridico.indicators.get_dashboard` (respects permissions and User
Permissions; filter by unit).

- Indicators: lawsuits in progress/closed, new ones (30 days), high risk (alert), not updated for more than 90 days
  (alert), draft records, most frequent subjects and CLM Legal Opinions ("Pareceres Jurídicos", only for those who
  can read them).
- Block code: `juridico/custom_blocks/`; applied idempotently by `juridico.setup.after_migrate`.
- The "Pareceres Jurídicos" shortcut points to `CLM Legal Evaluation` (only CLM Administrator/Manager/User and
  System Manager can read it).
- Workspace restricted to the roles: Usuário Jurídico, System Manager, HR Manager, HR User and CLM roles.
- `Processo Judicial` permissions come only from the DocType JSON (patch `alinhar_permissoes_processo_judicial`).
- Legacy "Contencioso" (litigation): patch `remover_contencioso_orfaos` removed Reports, empty `CJ *` DocTypes and CJ
  roles without users. Leftovers (`CJ *` DocTypes, orphan rows of ProcJud-2026-00001, tables and Module Def) were
  removed by patch `remover_contencioso_residuos`.
- Roles `RH/DP Contencioso` and `Financeiro Contencioso` were removed by patch `remover_papeis_contencioso` (no
  replacement).
