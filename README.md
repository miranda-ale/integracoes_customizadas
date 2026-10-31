# Integrações Customizadas (`integracoes_customizadas`)

Conjunto de integrações e customizações do ERPNext/HRMS para a BHCL. Versão atual: **3.0.0** (ver
[CHANGELOG.md](CHANGELOG.md)). O app reúne quatro frentes, que compartilham alguns serviços (por exemplo, o
`busca_cnpj` na importação Bionexo e o layout de e-mail do `clm`):

| Frente | Módulo | O que entrega |
| --- | --- | --- |
| Notificações por **WhatsApp** | Integracoes Customizadas | Evolution API v2, modelos com variantes, várias instâncias |
| **Jurídico** | Juridico | Processo Judicial com DataJud, gestão jurídica, provisão, agenda e relatórios |
| **Provas** | Provas | Banco de questões, provas e editais de processos seletivos |
| **Compras** | Integracoes Customizadas | Bionexo, Mapa de Preços, Nota Fiscal no recebimento, etapas do processo e workspaces enxutos |

Há ainda recursos transversais: [normalização de cadastros em caixa alta](#normalização-de-cadastros),
[verificação de acesso a DocTypes](#política-de-acesso-a-doctypes) e campos personalizados via fixtures.

## Funcionalidades

### Notificações por WhatsApp (Evolution API v2)

**Envio**

- Opção **Enviar também por WhatsApp** nas regras `Notification`. A regra exige um **Modelo WhatsApp** e envia o
  assunto e a mensagem aos usuários selecionados, no número do campo *Celular* (`mobile_no`) do cadastro de usuário.
- **Destinatários sem usuário:** campos *Phone* do documento (inclusive de tabelas filhas), escolhidos na tabela
  *Recipients*, e o campo **Números WhatsApp adicionais** (um por linha, aceita Jinja). Números repetidos recebem
  uma só mensagem.
- **Anexo do formato de impressão:** com "Attach Print" e um "Print Format" na regra, o PDF é gerado no envio
  (com as mesmas travas de rascunho e cancelado do e-mail) e enviado como documento; o texto vira a legenda.
  Limite de 15 MB.
- Números brasileiros com DDD recebem o prefixo 55 automaticamente; números internacionais devem ser informados
  completos, com `+` e código do país.

**Modelos e variantes**

- DocType **Modelo WhatsApp** com redações alternativas (**Variante Modelo WhatsApp**). O roteador sorteia uma
  variante por destinatário, sem repetir a anterior nem a última recebida pelo mesmo número; a função Jinja
  `sorteio("Oi","Olá")` varia trechos dentro da mensagem. O interruptor é **Variar mensagens** em Configurações
  WhatsApp.
- **Mínimo de 10 variantes ativas** para o modelo ficar ativo. Modelos criados por código recebem redações-semente
  (`seed/variantes_modelos.py`) e os patches `semear_variantes_modelo_whatsapp` e
  `completar_variantes_modelo_whatsapp` completam os existentes (os sem semente ficam no Error Log).
- Hooks de extensão: `whatsapp_contexto_extra` (variáveis extras no contexto do modelo) e
  `evolution_webhook_handlers`.

**Conexão e instâncias**

- **Configurações WhatsApp** (Single): URL base, chave global, instância principal, ativo, timeouts, intervalo entre
  envios e verificação prévia do número. Ações para **criar a instância** (informa se foi criada ou já existia),
  **gerar QR Code** e **atualizar o estado** da conexão.
- **Roteamento entre instâncias:** a tabela *Instâncias adicionais* (**Instancia WhatsApp**, com peso e limite diário
  opcionais) soma-se à principal; `whatsapp/distribuidor.py` usa a instância conectada de menor carga do dia, com
  afinidade por destinatário e failover. Sem linhas adicionais o comportamento não muda.
- **Conector estável** (`whatsapp/conector.py`): `estado_conexao`, `verificar_numero`, `enviar_texto`,
  `normalizar_numero_br`; sem retry em envio.
- **Envio WhatsApp:** registro por destinatário com estado, instância, variante, formato e arquivo, e botão
  **Reenviar** para falhas.
- O endpoint de webhook da Evolution está **reservado e desligado** (responde HTTP 501).
- E-mails das Notifications (canal E-mail), do Modelo WhatsApp (canal E-mail ou fallback) e do avanço de etapa do
  Edital usam o layout institucional do `clm` (`email_institucional.py`, dependência fraca).
- Configuração e registros de envio são restritos a administradores do sistema.

### Jurídico (módulo `Juridico`)

**Cadastro e DataJud**

- **Processo Judicial** em rascunho ou concluído, com número CNJ, tribunal, empresa, fase, risco, situação,
  assuntos e movimentações. Dados vindos do DataJud ficam protegidos contra edição manual.
- **Partes:** tabela de partes com parte principal, inclusive partes sem cadastro e identificação de
  ex-colaboradores; a opção *Terceiros* (pacientes) liga a Contatos.
- **Configurações DataJud:** consulta por número CNJ e tribunal, busca manual de andamentos e acompanhamento
  automático dos processos em andamento (dias úteis às 03:00, com distribuição para a fila longa). Timeout de
  100 s; em falha, os dados anteriores são preservados. Anexo por movimentação, com leitura de submovimentos.
- **Vínculos** com Colaborador, Cliente, Fornecedor, Contato e processos relacionados, nos painéis de conexões.

**Gestão jurídica (v3.0.0)**

- **Classificação interna:** natureza (Trabalhista, Cível, Tributário, Outros), tipo de ação, objeto, pasta/código
  interno (único por empresa) e responsável interno.
- **Advogados:** nome, OAB validada (`123456/SP`), escritório, tipo interno/externo e honorários.
- **Pedidos e provisão:** probabilidade de perda (Provável/Possível/Remota) e valor provável por pedido; a
  provisão sugerida soma os pedidos prováveis e pode ser sobrescrita (`provisao_manual`). A probabilidade do
  processo é a do pior pedido; o `risco` segue manual.
- **Audiências e prazos:** cada linha mantém um ToDo (e um Event, nas audiências) sem duplicar; encerra ao
  informar o resultado e cancela ao remover. Job diário às 07:00 alerta prazos vencidos ou a até 3 dias.
- **Financeiro:** depósitos judiciais/recursais, acordos e custas com totais calculados; resultado (procedente,
  improcedente, acordo) e data de encerramento.

**Indicadores e relatórios**

- **Dashboard View** *Processos Judiciais*: cartões (total, em andamento, encerrados) e gráficos por situação,
  risco, fase, tribunal, localidade IBGE e assuntos mais frequentes; painel **Juridico Indicadores** no workspace
  (ver [docs/juridico-dashboard.md](docs/juridico-dashboard.md)).
- Relatórios: **Relação de Processos** (filtros por empresa, parte, fase, situação, assunto, tribunal, grau, risco,
  natureza, responsável, número e período; impressão/PDF próprios), **Provisão de Processos**, **Passivo de
  Processos**, **Processos por Colaborador** e **Aging de Processos**.
- Workspace **Jurídico** (com atalho para Pareceres Jurídicos do `clm`) e papel **Usuário Jurídico**. O legado
  *Contencioso* foi removido por patches.

### Provas (módulo `Provas`)

- **Disciplina** e **Questão**: banco de questões por área de conhecimento, dificuldade e cargo (`Designation`),
  com alternativas e indicação da correta.
- **Prova** (submetível): composição a partir do banco de questões, vinculada a um Edital.
- **Edital**: processos seletivos com etapas e candidatos, integrado a *Job Applicant*, *Job Opening* e
  *Interview* do HRMS.
- **Relatórios:** Candidatos por Etapa, Candidatos por Status e Comparativo entre Editais.
- **Formatos de impressão:** Minuta de Edital, Prova Completa e Gabarito.
- Detalhes em [docs/modulo_provas.md](docs/modulo_provas.md) (o cabeçalho do documento ainda indica "Versão 0.1.0").

### Compras

**Bionexo**

- **Exportação:** botão *Exportar XML Bionexo* na `Request for Quotation` submetida, no layout XML da Bionexo.
- **Importação do PDF** (`Importacao Bionexo`, card *Bionexo* no workspace Compras ou botão *Importar PDF Bionexo*
  na cotação submetida): lê o "Relatório geral de PDC" e identifica o Pedido de Cotação (pelo nome gravado em
  Observações pelo XML exportado ou pelo ID Bionexo), os itens (`item_code` ou `custom_código_bionexo`) e os
  fornecedores (CNPJ completo; sem CNPJ válido no cadastro, pelo nome).
  - Fornecedores não cadastrados são criados com a consulta de CNPJ do `busca_cnpj` (sem ela, com nome e CNPJ do
    relatório); itens não identificados são relacionados à mão ou ignorados.
  - Ao submeter, gera um `Supplier Quotation` submetido por fornecedor e uma `Purchase Order` em rascunho por
    fornecedor com os itens "Confirmado" (quantidade e preço do Bionexo; data da OC = confirmação no Bionexo).
  - Janela de conclusão: orçamentos só dos itens confirmados e dos vencedores; a caixa *Gerar também orçamentos
    dos demais fornecedores* (marcada) inclui os demais com todos os itens cotados.
  - Solicitação de Compras sem Pedido de Cotação gera o Pedido de Cotação a partir do relatório. A empresa
    acompanha a Solicitação/Pedido escolhido (seção *Referências*).
  - O cancelamento exclui as OCs em rascunho, cancela os orçamentos e o Pedido de Cotação gerado.
- **Mapa de Preços RFQ:** relatório comparativo da `Request for Quotation` (item por linha, fornecedor por coluna),
  pelo botão *Mapa de Preços* da cotação.

**Recebimento e fluxo**

- **Nota Fiscal do Fornecedor** no Recebimento de Compra (número, série, chave de acesso validada, data, valor,
  anexo; editável após submeter); a Fatura de Compra herda `bill_no` e `bill_date`.
- Relatórios **Pedidos a Receber** (botão *Receber*) e **Recebidos a Faturar** (botão *Criar Fatura*).
- Barra **Etapas do processo** (Solicitação → Cotação → Pedido → Recebimento → Fatura) nos formulários da
  cadeia; documentos sem permissão de leitura são só contados.
- **Workspaces Compras e Estoque enxutos**, definidos em `compras/workspaces.py` e reaplicados a cada migrate.
- Seções de impostos recolhidas por padrão e rótulos da cadeia traduzidos para pt-BR.
- Ver [docs/fluxo-compras.md](docs/fluxo-compras.md).

### Normalização de cadastros

Nomes de Employee, Company, Supplier, Customer, Item, Contact, Address, Lead, Department e Designation ficam em
caixa alta e sem acento (hook `doc_events["*"]` em `normalizacao/maiusculas.py` e `maiusculas.js`). O patch
`maiusculas_nomes_existentes` aplica a regra aos registros antigos.

### Política de acesso a DocTypes

A cada `migrate`, `politicas/acesso_doctypes.py` avisa sobre DocTypes órfãos ou inalcançáveis do app (coberto por
`test_politica_acesso`).

### Campos personalizados (fixtures)

- Campos de `Employee` (documentos pessoais, dados trabalhistas, dependentes, PCD, etnia) e de `Designation` (CBO,
  escolaridade, conselho profissional, descrição de atividades).
- Papel `Usuário Jurídico` e Custom HTML Block `Relatórios`. O painel *Juridico Indicadores* é aplicado por código
  (`juridico.setup`), não por fixture.

## Requisitos

- Frappe v15 e os apps `erpnext`, `hrms`, `rh_brasil` e `busca_cnpj` (`required_apps`)
- `clm` (opcional): layout institucional de e-mail e atalhos de Pareceres/Documentos do Fornecedor
- Para WhatsApp: instância da [Evolution API](https://doc.evolution-api.com) v2
- Para o Jurídico: acesso à API pública do DataJud (CNJ)
- Para a importação Bionexo: `pypdf` (já presente no ambiente do Frappe; não declarado no `pyproject.toml`)

## Instalação

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/miranda-ale/integracoes_customizadas --branch develop
bench --site <site> install-app integracoes_customizadas
bench --site <site> migrate
```

O `migrate` executa os `after_migrate` (Provas, Jurídico, campo da Notification, card Bionexo, Compras e
verificação de acesso) e os patches pendentes.

## Configuração e uso do WhatsApp

1. Abra **Configurações WhatsApp** no Desk, informe URL base, chave global e nome da instância, e salve.
2. Clique em **Criar instância**, depois em **Gerar novo QR Code**; escaneie-o em *Aparelhos conectados* do
   WhatsApp e use **Atualizar estado** para confirmar a conexão. O mesmo botão renova a sessão. Para mais de um
   número, preencha *Instâncias adicionais* e repita o processo por instância.
3. Crie ou revise o **Modelo WhatsApp** (mínimo de 10 variantes ativas).
4. Nas regras **Notification** desejadas, marque **Enviar também por WhatsApp** e escolha o Modelo.
5. Consulte **Envio WhatsApp** para ver o resultado por destinatário e reenviar os registros com estado **Falhou**.

## Desenvolvimento

```text
integracoes_customizadas/
├── whatsapp/        # api, conector, distribuidor, roteador, modelos, delivery, notification, setup, webhook
├── juridico/        # datajud, parte, agenda, indicadores, relatorios, dashboard, setup, DocTypes, relatórios, workspace
├── provas/          # DocTypes, relatórios, formatos de impressão
├── bionexo/         # export_xml · import_pdf (leitura do PDF) · importacao · setup
├── compras/         # receipt (NF) · process_view (etapas) · workspaces · setup
├── normalizacao/    # maiusculas.py
├── politicas/       # acesso_doctypes.py
├── seed/            # variantes_modelos.py (redações-semente)
├── email_institucional.py
├── integracoes_customizadas/   # DocTypes de WhatsApp e Importacao Bionexo, relatórios Mapa de Preços RFQ, Pedidos a Receber, Recebidos a Faturar
├── patches/ · fixtures/ · public/ (css e js) · docs/
└── tests/           # 14 arquivos (WhatsApp, Bionexo, Compras, Jurídico, maiúsculas, política de acesso)
```

Há ainda `juridico/doctype/processo_judicial/test_processo_judicial.py`.

Testes (a partir da raiz do bench):

```bash
bench --site <site> run-tests --app integracoes_customizadas
```

O app usa `pre-commit` (ruff, eslint, prettier, pyupgrade):

```bash
cd apps/integracoes_customizadas
pre-commit install
```

## Documentação

- [CHANGELOG.md](CHANGELOG.md): histórico por versão
- [docs/fluxo-compras.md](docs/fluxo-compras.md)
- [docs/juridico-dashboard.md](docs/juridico-dashboard.md)
- [docs/modulo_provas.md](docs/modulo_provas.md)

## Licença

MIT
