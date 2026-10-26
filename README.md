# Integrações Customizadas (`integracoes_customizadas`)

Conjunto de integrações e customizações do ERPNext/HRMS para a BHCL. O app reúne quatro frentes independentes:
notificações por **WhatsApp**, módulo **Jurídico** (processos judiciais com DataJud), módulo de **Provas**
(processos seletivos) e ferramentas de **Compras** (Bionexo e Mapa de Preços de cotações).

## Funcionalidades

### Notificações por WhatsApp (Evolution API v2)

- Opção **Enviar também por WhatsApp** nas regras `Notification`: os usuários já selecionados pela regra recebem
  o assunto e a mensagem no número do campo *Celular* (`mobile_no`) do cadastro de usuário.
- DocType **Configurações WhatsApp** (Single): URL base da Evolution API, chave global e nome da instância, com
  ações para **criar a instância**, **gerar QR Code** e **atualizar o estado** da conexão.
- DocType **Envio WhatsApp**: registro de cada envio por usuário, com estado e botão **Reenviar** para falhas.
- Números brasileiros com DDD recebem o prefixo 55 automaticamente; números internacionais devem ser informados
  completos, com `+` e código do país. Se a regra marcar "Attach Print" e um "Print Format", o PDF segue como documento e o texto vira a legenda.
- Configuração e registros de envio são restritos a administradores do sistema.

### Jurídico (módulo `Juridico`)

- **Processo Judicial**: cadastro em rascunho ou concluído, com número CNJ, tribunal, empresa, parte, fase,
  risco, situação, assuntos e movimentações. Dados vindos do DataJud ficam protegidos contra edição manual.
- **Integração DataJud** (`Configurações DataJud`): consulta por número CNJ e tribunal, busca manual de
  andamentos e acompanhamento automático dos processos em andamento (agendamento em dias úteis às 03:00, com
  distribuição para a fila longa). Em caso de falha, os dados anteriores são preservados.
- **Vínculos** com Colaborador, Cliente, Fornecedor, Contato (inclui a opção *Terceiros* para pacientes) e
  processos relacionados, exibidos nos painéis de conexões dessas telas.
- **Indicadores**: Dashboard View *Processos Judiciais*, com cartões (total, em andamento, encerrados) e gráficos
  por situação, risco, fase, tribunal, localidade IBGE e assuntos mais frequentes.
- **Relação de Processos**: relatório com filtros por empresa, parte, fase, situação, assunto, tribunal, grau,
  risco, número e período de ajuizamento, com impressão/PDF próprios.
- Workspace **Jurídico** e papel **Usuário Jurídico**.

### Provas (módulo `Provas`)

- **Disciplina** e **Questão**: banco de questões por área de conhecimento, nível de dificuldade e cargo
  (`Designation`), com alternativas e indicação da correta.
- **Prova** (submetível): composição de provas a partir do banco de questões, vinculada a um Edital.
- **Edital**: gestão de editais de processos seletivos, com etapas e candidatos, integrado a *Job Applicant*,
  *Job Opening* e *Interview* do HRMS.
- **Relatórios**: Candidatos por Etapa, Candidatos por Status e Comparativo entre Editais.
- **Formatos de impressão**: Minuta de Edital, Prova Completa e Gabarito.
- Detalhes em [docs/modulo_provas.md](docs/modulo_provas.md).

### Compras

- **Exportação Bionexo**: botão *Exportar XML Bionexo* na `Request for Quotation` submetida, que baixa a cotação
  no layout XML da Bionexo.
- **Importação do PDF Bionexo** (`Importacao Bionexo`, card *Bionexo* no workspace Compras ou botão *Importar PDF
  Bionexo* na `Request for Quotation` submetida): lê o "Relatório geral de PDC" do Bionexo e identifica o Pedido de
  Cotação (pelo nome gravado em Observações pelo XML exportado ou pelo ID Bionexo), os itens (código = `item_code`
  ou `custom_código_bionexo`) e os fornecedores (CNPJ completo; sem CNPJ válido no cadastro, pelo nome).
  Fornecedores não cadastrados são criados com a consulta de CNPJ do `busca_cnpj` (sem ela, com nome e CNPJ do
  relatório); itens não identificados são relacionados à mão aos itens do Pedido de Cotação ou ignorados. Sem
  identificação automática, Solicitação de Compras e Pedido de Cotação filtram um ao outro. Ao submeter, gera um
  `Supplier Quotation` submetido por fornecedor que cotou e uma `Purchase Order` em rascunho por fornecedor com os
  itens "Confirmado" (quantidade e preço do Bionexo); o cancelamento exclui essas OCs em rascunho e cancela os
  orçamentos.
- **Mapa de Preços RFQ**: relatório comparativo de uma `Request for Quotation` (um item por linha, um fornecedor
  por coluna), acessível pelo botão *Mapa de Preços* da própria cotação.

### Campos personalizados (fixtures)

- Campos de `Employee` (documentos pessoais, dados trabalhistas, dependentes, PCD, etnia) e de `Designation` (CBO,
  escolaridade, conselho profissional, descrição de atividades), exportados como fixtures.
- Papel `Usuário Jurídico` e Custom HTML Block `Relatórios`.

## Requisitos

- Frappe v15, ERPNext e HRMS (`required_apps = ["erpnext", "hrms"]`)
- Para WhatsApp: instância da [Evolution API](https://doc.evolution-api.com) v2
- Para o Jurídico: acesso à API pública do DataJud (CNJ)

## Instalação

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/miranda-ale/integracoes_customizadas --branch develop
bench --site <site> install-app integracoes_customizadas
bench --site <site> migrate
```

## Configuração e uso do WhatsApp

1. Abra **Configurações WhatsApp** no Desk, informe URL base, chave global e nome da instância, e salve.
2. Clique em **Criar instância**, depois em **Gerar novo QR Code**; escaneie-o em *Aparelhos conectados* do
   WhatsApp e use **Atualizar estado** para confirmar a conexão. O mesmo botão renova a sessão quando preciso.
3. Nas regras **Notification** desejadas, marque **Enviar também por WhatsApp**.
4. Consulte **Envio WhatsApp** para ver o resultado por usuário e reenviar os registros com estado **Falhou**.

## Desenvolvimento

```text
integracoes_customizadas/
├── whatsapp/      # api, delivery, override de Notification
├── juridico/      # datajud.py, DocTypes, relatório, dashboard, workspace
├── provas/        # DocTypes, relatórios, formatos de impressão
├── bionexo/       # export_xml.py · import_pdf.py (leitura do PDF) · importacao.py · setup.py
├── integracoes_customizadas/   # DocTypes de WhatsApp e Importacao Bionexo, relatório Mapa de Preços RFQ
├── patches/ · fixtures/ · public/js/
└── tests/         # test_whatsapp.py · test_bionexo_export.py · test_bionexo_import.py
```

Testes (a partir da raiz do bench):

```bash
bench --site <site> run-tests --app integracoes_customizadas
```

O app usa `pre-commit` (ruff, eslint, prettier, pyupgrade):

```bash
cd apps/integracoes_customizadas
pre-commit install
```

Histórico de versões em [CHANGELOG.md](CHANGELOG.md).

## Licença

MIT
