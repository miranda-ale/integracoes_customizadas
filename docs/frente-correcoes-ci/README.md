# Frente de correções de produto reveladas pelo CI: integracoes_customizadas

Registro de 2026-11-23. Branch: `claude/frappe-ci-product-fixes-ag289b`. Sem PR. HEAD antes desta documentação: `da5d69f`.
Este retrato pode ficar desatualizado: confira `git log`, o PR e os checks reais antes de agir.

## O que foi feito
- Padrão de CI, cadastros de produção (`cadastros/`: Municípios, CBO, Dependentes, Colaboradores Link e Canal de Denúncias),
  campos Bionexo na instalação limpa, atalhos de workspace e política de acesso restrita aos módulos do app, traduções
  removidas (dono: `bhcl_theme`), Designation relaxado só no teste. Semgrep de 66 para 2.

## Estado
- HEAD `da5d69f`: Server **success**; Frappe Linter **vermelho** por 2 achados. Revisor aprovou com ressalvas.
- **Correções do revisor NÃO aplicadas** (o agente caiu por limite de gasto): `renderizar_modelo`
  (`whatsapp/notification.py`) perdeu `safe_render_flags()` e o tratamento de `TemplateError`; README, CHANGELOG, `ci.yml`
  (`permissions` e concurrency), log de papel inexistente e ADR-003.

## Pendências
- `webhook_evolution` (`whatsapp/webhook.py:32`, guest sem HMAC, responde 501): recomendação, remover.
- `override_doctype_class` (`hooks.py:146`): recomendação, `# nosemgrep` específico mais teste de deriva.
- Canal de Denúncias (LGPD): `den_nome` e `den_email` sem permlevel; HR User deleta, exporta e compartilha. Risco já
  existe em produção; exige decisão e Custom DocPerm ou patch.
- Dono dos 4 cadastros (conflito com o `rh_brasil`) e do módulo "Gestor Online".
- Reescrita do histórico para remover os `.whl` do commit `28c3194`: **em espera**; o espaço quase não é liberado porque
  `refs/pull/7/head` não pode ser reescrito (só o suporte do GitHub).

## Arquivos desta pasta
- `prompt-nova-sessao.md`: contexto completo da frente, com as regras permanentes, os padrões institucionais, as decisões
  do usuário e o estado de **todos** os apps. Cópia idêntica em cada repositório.
- `setup-ambiente-frappe.sh`: script único de ambiente (bench, MariaDB, Redis, `payments`, `erpnext`, `hrms` e os apps
  clonados). **Nunca foi executado de ponta a ponta**; só a sintaxe e a lógica do `frappe-env` foram validadas.

## Regras que valem aqui
CI verde sempre; nenhum `# nosemgrep`, skip ou job desativado sem aprovação explícita; todo bug corrigido ganha teste;
Semgrep em varredura completa; arredondamento monetário proibido (truncar na 2ª casa); PR só depois de revisor isolado.
