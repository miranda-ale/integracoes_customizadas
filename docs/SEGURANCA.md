# Segurança, Sigilo e LGPD — Contencioso (PT-BR)

## 1. Papéis (Roles) sugeridos
- **CJ Administrador**: controle total do módulo (configurações, permissões, fixtures, relatórios).
- **CJ Gestor Jurídico**: gestão do contencioso, acessa tudo exceto configurações administrativas sensíveis.
- **CJ Analista Jurídico**: operacional (cadastros, eventos, prazos, audiências, documentos).
- **CJ Visualizador**: somente leitura do módulo (não sigiloso).
- **Visualizador Executivo**: somente painéis agregados e relatórios consolidados, sem detalhes sensíveis.
- **Financeiro Contencioso**: acesso a itens financeiros e relatórios financeiros (respeitando sigilo).
- **RH/DP Contencioso**: acesso restrito a campos trabalhistas necessários (respeitando sigilo).

> Ajuste os nomes para o padrão interno da organização se necessário, mantendo a intenção.

---

## 2. Classificação de sigilo (campo do Processo)
Campo: `cj_nivel_sigilo`
- **Publico**: visível para CJ Visualizador e perfis executivos (com restrição de dados sensíveis).
- **Restrito**: visível para roles CJ (jurídico) e Financeiro Contencioso (conforme necessidade).
- **Sigiloso**: visível apenas para **CJ Administrador** e **CJ Gestor Jurídico**.

---

## 3. Regras mínimas de acesso
- Processos **Sigilosos**:
  - bloquear leitura para perfis não jurídicos, mesmo que tenham acesso à `company`.
- Documentos marcados como `cj_confidencial`:
  - restringir visualização apenas a roles jurídicas (e/ou conforme `cj_nivel_sigilo`).
- Evitar exposição de CPF/CNPJ em telas e relatórios executivos:
  - se armazenar identificadores, aplicar mascaramento na UI/relatórios para perfis não jurídicos.

### Implementação (Fase 1)
- `permission_query_conditions`/`has_permission` no DocType **Processo Judicial** filtram por `cj_nivel_sigilo`.
- Máscara de CPF/CNPJ aplicada na UI do Processo Judicial quando o valor aparenta ser um documento (11/14 dígitos).
- Documentos com `cj_confidencial=1` são ocultados na grid para perfis não jurídicos.

---

## 4. Auditoria e trilha de evidências
- Ativar **Versioning** no DocType Processo Judicial (se disponível/viável).
- Garantir registro de `modified_by`, `modified`, e manter histórico de risco via `cj_historico_risco`.
- Integrações (stub):
  - logs em `cj_log_sync` e registro de última execução.

---

## 5. Multiempresa / Unidades
- O campo `company` é obrigatório no Processo Judicial.
- Permissões devem respeitar Company (quando aplicável), mas **sigilo** tem prioridade sobre Company.
