# Relatórios e Dashboards — Contencioso (PT-BR)

## 1) Relatórios mínimos (Fase 1)

### R01 — Prazos a vencer (próximos 30 dias)
- Filtros:
  - company
  - cj_responsavel_usuario (do processo) e/ou cj_responsavel_usuario (do prazo)
  - intervalo de vencimento
  - cj_status_prazo
  - cj_nivel_sigilo (comportamento conforme role)
- Colunas:
  - Processo (link)
  - CNJ
  - Tipo do Prazo
  - Data de Vencimento
  - Responsável
  - Status do Prazo
  - Nível de Sigilo

### R02 — Exposição e Provisão por mês e por unidade
- Agrupar por:
  - mês (competência)
  - company
- Métricas:
  - soma de `cj_valor_pedido`
  - soma de `cj_valor_estimado`
  - soma de `cj_provisao_atual`
- Complementos:
  - comparação mês anterior (quando possível)

### R03 — Processos por Status e Fase
- Contagem por:
  - `cj_status`
  - `cj_fase`
- Filtros:
  - company
  - tipo de processo
  - período (data distribuição / última movimentação)

### R04 — Custos do Contencioso por período
- Baseado em `cj_itens_financeiros`
- Agrupar por:
  - mês
  - tipo (custas, honorários, acordo etc.)
- Filtros:
  - company
  - intervalo de datas
  - tipo financeiro

---

## 2) Dashboards (Fase 1)

### Dashboard Executivo
KPIs:
- total de processos ativos
- soma de provisão atual
- soma de exposição estimada
- prazos nos próximos 15 dias
- custos no ano (YTD)

Gráficos/Listas:
- provisão por mês
- processos por status
- top tipos de pedidos (texto, simples) — quando preenchido em `cj_tipos_pedidos`

> Regras: dashboard executivo não deve revelar detalhes de processos Sigilosos.

### Dashboard Jurídico
KPIs:
- total de processos por fase
- prazos a vencer (7/15/30 dias)
- audiências futuras (próximos 30 dias)

Listas:
- processos recentemente atualizados
- prazos vencidos
- audiências futuras

---

## 3) Implementação recomendada no ERPNext/Frappe
- Relatórios:
  - começar com **Query Report** (rápido) quando possível
  - migrar para **Script Report** se precisar de lógica de sigilo, agregações complexas ou mascaramento
- Dashboards:
  - usar Dashboard Charts e Number Cards quando possível
  - garantir filtros por Company e regras de sigilo

## 4) Implementado (Fase 1)
Relatórios (Script Report):
- **Prazos a vencer**
- **Exposição e Provisão por mês**
- **Processos por Status e Fase**
- **Custos do Contencioso por período**

Dashboards (Desk > Dashboard):
- **Dashboard Executivo** (cards + charts)
- **Dashboard Jurídico** (cards + charts)
