# Filtro de List View por User Permission de Item Group

**Data:** 2026-07-09  
**App:** `integracoes_customizadas`  
**Módulo:** `permissions/item_group_access.py`  
**Release:** tag **`v1.5.0`** em `develop` (commit `742b4f1`)  
**Repo:** https://github.com/miranda-ale/integracoes_customizadas  

> Junto com esta tag, o tema/login/traduções foram removidos deste app  
> (migrados para `bhcl_theme` / https://github.com/still-pulse/theme_bhcl_erp_next `v0.2.0`).

## Problema

User Permission em **Item Group** restringe corretamente a busca de **Item** (campos Link), mas a **List View** de documentos (ex.: Solicitação de Compras / Material Request) listava **todos** os documentos. Ao abrir um documento com itens de outro grupo, o Frappe bloqueava — ou seja, a listagem vazava existência de documentos.

## Solução

Hooks padrão do Frappe (sem alterar core ERPNext):

| Hook | Função |
|------|--------|
| `permission_query_conditions` | Injeta SQL em `get_list` / List View / vários reports |
| `has_permission` | Reforça a mesma regra na abertura do documento |

**Regra:** se o usuário tem User Permission de Item Group aplicável ao DocType, só enxerga documentos cujos **todos** os itens estão em grupos permitidos (inclui descendentes do grupo, via expansão nativa do Frappe quando `hide_descendants=0`).

## DocTypes cobertos

Material Request, Request for Quotation, Supplier Quotation, Purchase Order, Purchase Receipt, Purchase Invoice, Quotation, Sales Order, Delivery Note, Sales Invoice, Stock Entry, Pick List, Stock Reconciliation, BOM, Work Order, Asset Capitalization.

## Arquivos

- `integracoes_customizadas/permissions/item_group_access.py`
- `integracoes_customizadas/permissions/__init__.py`
- `integracoes_customizadas/hooks.py` (registros)

## Teste manual

1. Criar User Permission: Allow = Item Group, For Value = `Serviços`, Apply to all DocTypes.
2. Login com esse usuário.
3. List View de Solicitação de Compras: só MRs com itens de Serviços (e subgrupos).
4. Confirmar que MRs de outros grupos **não aparecem**.
5. Abrir um MR permitido: ok.
6. Remover a User Permission: lista volta ao normal.

## Notas

- Administrator não é filtrado.
- Usuário **sem** User Permission de Item Group: sem filtro extra.
- `applicable_for` é respeitado (só filtra DocTypes aplicáveis).
- Não usa gambiarra de frontend; filtro no backend antes do response.
