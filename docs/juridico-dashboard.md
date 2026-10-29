# Dashboard do Jurídico

Workspace `Jurídico`: painel `Juridico Indicadores` (Custom HTML Block, mesmo padrão de RH/SESMT/CLM) alimentado por
`integracoes_customizadas.juridico.indicadores.get_dashboard` (respeita permissões e User Permissions; filtro por unidade).

- Indicadores: processos em andamento/encerrados, novos (30 dias), risco alto (alerta), sem atualização há mais de
  90 dias (alerta), cadastros em rascunho, assuntos mais frequentes e Pareceres Jurídicos do CLM (só para quem lê).
- Código do bloco: `juridico/custom_blocks/`; aplicado de forma idempotente por `juridico.setup.after_migrate`.
- Atalho "Pareceres Jurídicos" aponta para `CLM Legal Evaluation` (somente CLM Administrator/Manager/User e System Manager leem).
- Workspace restrito aos papéis: Usuário Jurídico, System Manager, HR Manager, HR User e papéis CLM.
- Permissões de `Processo Judicial` vêm só do JSON do DocType (patch `alinhar_permissoes_processo_judicial`).
- Legado Contencioso: patch `remover_contencioso_orfaos` removeu Reports, DocTypes `CJ *` vazios e papéis CJ sem usuário.
  Resíduos (DocTypes `CJ *`, linhas órfãs do ProcJud-2026-00001, tabelas e Module Def) removidos pelo patch `remover_contencioso_residuos`.
- Papéis `RH/DP Contencioso` e `Financeiro Contencioso` removidos pelo patch `remover_papeis_contencioso` (sem substituto).
