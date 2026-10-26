# Fluxo de compras de materiais: recebimento, Nota Fiscal e etapas

## Ciclo no ERPNext

`Material Request → (Request for Quotation → Supplier Quotation) → Purchase Order → Purchase Receipt → Purchase Invoice`

Cotação (RFQ e Supplier Quotation) é opcional. Os vínculos ficam nas linhas dos itens (`material_request`,
`supplier_quotation`, `purchase_order`, `purchase_receipt`); o Pedido de Compra acompanha `per_received` e
`per_billed`. Compra de serviços segue a cadeia própria do `clm` e não passa por aqui.

## Fluxo da BHCL

1. **Compras** fecha o Pedido de Compra.
2. A **unidade** abre o relatório **Pedidos a Receber** (atalho nos workspaces Compras e Estoque).
   Só aparecem pedidos submetidos, não recebidos por completo, com ao menos um item de estoque e dentro dos
   *User Permissions* do usuário (Company/Warehouse). *Receber* abre um Recebimento de Compra já preenchido.
3. No recebimento a unidade confere as quantidades e preenche a seção **Nota Fiscal do Fornecedor**: número, série,
   chave de acesso, data, valor e anexo. A chave é validada (44 posições e dígito verificador, inclusive CNPJ
   alfanumérico) e preenche número e série. Os campos podem ser preenchidos depois de submeter.
4. **Compras/Financeiro** abre **Recebidos a Faturar**: recebimentos submetidos ainda não faturados, com a NF
   informada, a diferença para o valor recebido e o botão *Criar Fatura*. A Purchase Invoice herda `bill_no` e
   `bill_date` do recebimento (se houver um único recebimento de origem).

Avisos (nunca bloqueiam): número divergente da chave, CNPJ do emitente diferente do fornecedor (só quando o
`tax_id` tem 14 caracteres), valor da NF diferente do recebido (tolerância: o maior entre R$ 1,00 e 0,5%).

## Permissões

Não há papel novo. O `Stock User` já cria e submete Purchase Receipt e lê Purchase Order; **não** acessa Purchase
Invoice. Criar *Custom DocPerm* substituiria todas as permissões padrão do DocType, por isso não foi usado.
Cada unidade fica restrita à sua Company/Warehouse por *User Permission*. Relatórios: *Pedidos a Receber* para Stock
User/Manager e Purchase User/Manager; *Recebidos a Faturar* para Purchase e Accounts User/Manager.

## Etapas do processo

Barra recolhível no topo de Material Request (tipo Purchase), RFQ, Supplier Quotation, Purchase Order, Purchase
Receipt e Purchase Invoice, no mesmo padrão do `clm` (`clm_process_steps`). Seis nós: Solicitação de Compras, **Pedido de
Cotação** e **Cotação do Fornecedor** (os dois dentro de um contorno tracejado "Cotação · opcional", pois a compra
pode seguir direto da Solicitação para a Ordem), Ordem de Compra, Recebimento de Compra e Nota Fiscal de Compra (mesmos
nomes usados no resto do sistema).

- `compras/process_view.py`: `get_purchase_steps(doctype, name)` descobre a cadeia pelos vínculos dos itens (até 150
  documentos), ignorando permissões, e marca como `restricted` o que o usuário não lê (só entra na contagem). Por
  isso a unidade vê a fatura como etapa existente sem ter acesso a ela.
- Status: `ok`, `pending`, `warn`, `none`. Alertas: entrega atrasada (`schedule_date`), recebimento parcial,
  recebido sem NF, valor da NF divergente, recebimento aguardando fatura. Cancelados são ignorados.
- A lista de etapas existe em Python (`STAGES`) e em JS (`compras.steps.STEPS`): mantenha as duas iguais.
- Front-end: `public/js/compras_steps.js` e `public/css/compras_steps.css` (carregados por `app_include_*`;
  incremente o `?v=` do `hooks.py` a cada mudança).

## Formulário do Recebimento de Compra

`compras/setup.py` (`after_migrate`, idempotente) cria os Custom Fields `custom_compras_nf_*` e deixa recolhidas
por padrão as seções de impostos do Recebimento (*Impostos e Taxas* e *Detalhamento de Impostos e Taxas*), do Pedido
e da Fatura de Compra (*Impostos e Taxas*), como *Desconto Adicional*. Rótulos em inglês de toda a cadeia
(MR, RFQ, SQ, PO, PR, PI e itens) foram traduzidos em `bhcl_theme/translations/pt*.csv`; o cliente busca a chave
exata (inclusive espaço no fim, como em `"Accounting Dimensions "`), e `tests/test_traducoes_compras.py` avisa
quando um rótulo novo aparece sem tradução.

## Workspaces Compras e Estoque

O layout dos dois workspaces é definido em `compras/workspaces.py` (`LAYOUTS`) e reaplicado a cada `migrate`; ajustes
feitos pela tela nesses dois workspaces são sobrescritos. Para mudar, edite `LAYOUTS`. A função só salva quando algo
mudou, e alvos inexistentes (ex.: relatório removido do ERPNext) são ignorados.

- **Compras** (time de compras): atalhos na ordem do fluxo (Solicitação → Pedido de Cotação → Cotação → Ordem →
  Pedidos a Receber → Recebimento → Recebidos a Faturar → Nota Fiscal), com contadores sem filtro de empresa (respeitam
  as User Permissions), e os cards Fluxo de compras, Bionexo, Cadastros (Fornecedor, Item, Lista de Preços),
  Relatórios e Configurações.
- **Estoque** (almoxarifado): atalhos Pedidos a Receber, Recebimento, Movimento de Estoque, Saldo, Solicitação e
  Item; cards Fluxo do recebimento e estoque, Consultas, Cadastros (só Item) e Configurações. Sem cartões numéricos
  nem gráfico.
- Cada workspace abre com um card do seu fluxo, numerado (num teste de uso, as pessoas não notavam os atalhos, só os
  cards). Em Compras, **Fluxo de compras**: 1. Solicitação de Compras … 8. Nota Fiscal de Compra. Em Estoque,
  **Fluxo do recebimento e estoque**: 1. Pedidos a Receber, 2. Recebimento de Compra, 3. Movimento de Estoque,
  4. Saldo de Estoque, 5. Solicitação de Compras (reposição). Cada usuário vê só os links que pode ler.
- Saíram as funções sem uso no site (0 registros em out/2026: Delivery Note, Pick List, Serial No, Scorecard,
  Product Bundle, Pricing Rule, Quality Inspection, Landed Cost etc.), os atalhos Learn/Dashboard e a cópia antiga
  em inglês dos links. Cópia do estado anterior: dump do `Workspace` antes da mudança (não versionado).
- Um card só aparece com os links que o usuário pode ler; Configurações some para quem só tem Stock User.
- As unidades com o módulo Compras ou Estoque bloqueado pelo Perfil de Módulos continuam sem ver esses workspaces.

## Testes

`bench --site dev run-tests --app integracoes_customizadas --module integracoes_customizadas.tests.test_compras_process`
(e `test_workspaces_compras`, `test_traducoes_compras`)
