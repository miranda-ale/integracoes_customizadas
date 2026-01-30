# Workflows — Contencioso / Processos Judiciais (PT-BR)

## 1) Workflow: Processo Judicial

### Estados sugeridos
- Rascunho
- Aberto
- Em Análise
- Em Andamento
- Sentença
- Recursos
- Execução
- Encerrado
- Arquivado

> Adaptação técnica (Frappe): criado o campo `cj_estado_workflow` (Select) para armazenar o estado do workflow, pois o Frappe exige um campo dedicado para o controle de estado.

### Transições (exemplo)
- Rascunho -> Aberto (Jurídico / Gestor)
- Aberto -> Em Análise (Jurídico)
- Em Análise -> Em Andamento (Jurídico)
- Em Andamento -> Sentença (Jurídico)
- Sentença -> Recursos (Jurídico)
- Recursos -> Execução (Jurídico)
- Execução -> Encerrado (Jurídico / Gestor)
- Encerrado -> Arquivado (Gestor)

### Regras de validação recomendadas
- Ao transitar para **Encerrado**:
  - exigir preenchimento de `cj_resultado_final`
  - exigir `cj_data_encerramento`
  - exigir ao menos 1 documento de categoria "Sentença" ou "Acordo" em `cj_documentos`
- Ao transitar para **Arquivado**:
  - status do processo (`cj_status`) deve ser "Arquivado"
  - processo já deve estar "Encerrado"

> Observação: as validações podem ser implementadas via `validate()` no DocType Processo Judicial, condicionadas ao estado do workflow.

---

## 2) Workflow: CJ Prazo (Child)

> Adaptação técnica: o workflow foi configurado sobre o DocType da child table. Em UI, as transições seguem o campo `cj_status_prazo` e o scheduler atualiza para "Vencido" quando aplicável.

### Estados
- A Vencer
- Vencido
- Cumprido
- Cancelado

### Transições
- A Vencer -> Cumprido (com registro de data/hora e observação)
- A Vencer -> Cancelado (com justificativa)
- A Vencer -> Vencido (automático por scheduler, quando `cj_data_vencimento` < hoje)
- Vencido -> Cumprido (com justificativa)
- Vencido -> Cancelado (com justificativa)

### Regras
- Ao marcar como Cumprido:
  - preencher `cj_concluido_em`
  - manter `cj_observacao_conclusao` (se estava Vencido, exigir justificativa mínima)
