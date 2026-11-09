# Histórico de alterações

Versões e datas seguem as tags do repositório (`vMAJOR.MINOR.PATCH`). A atribuição dos itens de WhatsApp às versões v1.14.0–v1.17.x segue as mensagens de commit; a tag v1.12.0 e a v1.13.0 (sem tag) não têm detalhamento.

## v4.0.3 — Mapa de Preços RFQ filtrado na primeira visita · 2026-11-09

- O botão "Mapa de Preços" abre o relatório já filtrado pela origem na primeira visita: usa `route_options` em vez de `set_filter_value` após `set_route`, que corria contra o carregamento do relatório.

## v4.0.2 — Estilos dos indicadores jurídicos · 2026-11-08

- O bloco de indicadores combina o layout local com o CSS de contraste do `bhcl_theme`, com fallback para `ind_alerta.css` quando o tema não está instalado. Os estilos permanecem disponíveis dentro do Shadow DOM do bloco.
- Remove regras de alerta duplicadas do CSS local do Jurídico.

## v4.0.1 — Declarações de dependências · 2026-11-02

- `scripts/install_system_deps.sh` usa o Python do bench e cai para `tomli` no Python 3.10 (`tomllib` só existe a partir do 3.11).

## v4.0.0 — DocTypes de Tipo de Deficiência · 2026-11-02

- **Tipo de Deficiencia** e **Tipo de Deficiencia Item** passam a ser entregues pelo app. O Custom Field `Employee.custom_tipo_de_deficiencia` (Table MultiSelect) apontava para um DocType que só existia no banco de produção, e em site novo o fixture `custom_field.json` era ignorado ("DocType Tipo de Deficiencia Item not found").
- `required_apps` fixa `frappe/erpnext@version-15`, `frappe/hrms@version-15`, `still-pulse/rh_brasil@main` e `miranda-ale/busca_cnpj@main` (uma linha só: o bench lê com regex). O README usava `--branch develop` (inexistente).
- `scripts/install_system_deps.sh` instala os pacotes apt declarados em `[deploy.dependencies.apt]` pelos apps do bench (`--dry-run` só lista).

## v3.0.0 — Gestão jurídica do Processo Judicial (Fase 3) · 2026-10-30

- **Classificação interna:** natureza (Trabalhista, Cível, Tributário, Outros), tipo de ação, objeto, pasta/código interno (único por empresa) e responsável interno; `track_changes` ligado; patch marca os processos existentes como Trabalhista.
- **Advogados:** tabela com nome, OAB validada (`123456/SP`), escritório, tipo interno/externo e honorários.
- **Pedidos e provisão:** tabela de pedidos com probabilidade de perda (Provável/Possível/Remota) e valor provável; provisão sugerida pela soma dos pedidos prováveis, sobrescrevível (`provisao_manual`); probabilidade do processo = a do pior pedido; `risco` segue manual.
- **Audiências e prazos:** tabela que mantém um ToDo (e um Event nas audiências) por linha sem duplicar, encerra ao informar o resultado e cancela ao remover; job diário às 07:00 alerta prazos vencidos ou a até 3 dias (`juridico/agenda.py`).
- **Financeiro:** depósitos judiciais/recursais, acordos e custas com totais calculados; resultado (procedente/improcedente/acordo) e data de encerramento. Campos do DataJud seguem imutáveis.
- **Relatórios:** Provisão de Processos, Passivo de Processos, Processos por Colaborador e Aging de Processos, reutilizando os filtros da Relação de Processos (`montar_filtros`/`listar_processos`), que ganhou filtros por natureza e responsável.
- **Lista:** Nome da Parte volta a aparecer na lista do Processo Judicial (Natureza e Grau saem da lista e seguem como filtros).
- Inclui as Fases 1 e 2 (v2.4.0): partes sem cadastro e tabela de partes com parte principal.

## v2.4.0 — Partes do Processo Judicial · 2026-10-30

- **Partes:** tabela de partes com parte principal e partes sem cadastro; identificação de ex-colaboradores.

## v2.3.1 — Fechamento do ciclo da v2.3.0 · 2026-10-29

- Tag no commit de merge; sem mudança funcional.

## v2.3.0 — Painel de indicadores do Jurídico · 2026-10-29

- **Painel "Juridico Indicadores"** (Custom HTML Block aplicado por `juridico.setup`, ver `docs/juridico-dashboard.md`).
- Atalho de **Pareceres Jurídicos** (clm) no workspace Jurídico.
- Saneamento de permissões do Processo Judicial e remoção do legado **Contencioso** (patches `remover_contencioso_orfaos`, `remover_contencioso_residuos`, `remover_papeis_contencioso`).

## v2.2.4 — Timeout do DataJud · 2026-10-29

- Timeout ampliado para 100 s; a consulta que estoura a leitura não é repetida.

## v2.2.3 — Lint · 2026-10-29

- ruff, prettier e eslint em todo o app; corrigido filtro duplicado em Prova e `msgprint` com globais implícitas.

## v2.2.2 — Atalhos de Documentos do Fornecedor · 2026-10-29

- Atalhos de Documentos do Fornecedor (clm) no workspace Compras.

## v2.2.1 — CI · 2026-10-28

- commitlint, linter e CI do Frappe.

## v2.2.0 — Nomes em caixa alta · 2026-10-28

- **Normalização de cadastro:** nomes de Employee, Company, Supplier, Customer, Item, Contact, Address, Lead, Department e Designation ficam em caixa alta e sem acento (hook global `doc_events["*"]` em `normalizacao/maiusculas.py`, `maiusculas.js` e patch `maiusculas_nomes_existentes` para os registros antigos).

## v2.1.1 — Bionexo · 2026-10-26

- A importação do PDF aceita item sem cotação de fornecedor.

## v2.1.0 — Compras: Nota Fiscal, etapas e workspaces enxutos · 2026-10-26

- **Recebimento com Nota Fiscal:** seção *Nota Fiscal do Fornecedor* no Recebimento de Compra (número, série, chave de acesso validada, data, valor, anexo; editável após submeter) e herança de `bill_no`/`bill_date` pela Fatura de Compra (`compras/receipt.py`).
- **Relatórios** *Pedidos a Receber* (botão *Receber*) e *Recebidos a Faturar* (botão *Criar Fatura*) no card *Recebimento de Compras* dos workspaces Compras e Estoque.
- **Barra *Etapas do processo*** (Solicitação → Cotação → Pedido → Recebimento → Fatura) nos formulários da cadeia, no padrão do clm; documentos sem permissão de leitura são só contados. Pedido de Cotação e Cotação de Fornecedor são nós separados, dentro do grupo tracejado *Cotação · opcional*. Ver `docs/fluxo-compras.md`.
- **Workspaces Compras e Estoque enxutos**, definidos em código (`compras/workspaces.py`) e reaplicados a cada migrate: atalhos na ordem do fluxo com contadores por usuário, poucos cards e só funções usadas no site (de 141/144 para 19/18 linhas de link); card numerado do fluxo em primeiro em cada um; saíram cartões numéricos, gráfico, Grupo de Fornecedores, Preço do Item, Grupo de Itens, Marca, Armazém, Unidade de Medida, atalhos Learn/Dashboard e a cópia antiga em inglês dos links.
- Seções de impostos do Recebimento, do Pedido e da Fatura de Compra recolhidas por padrão; rótulos de toda a cadeia (Solicitação a Fatura) traduzidos para pt-BR.

## v2.0.0 — Importação do PDF Bionexo · 2026-10-26

- Novo DocType `Importacao Bionexo` (e filhos Cotação, Fornecedor e Item) lê o "Relatório geral de PDC" (pypdf), relaciona Pedido de Cotação/Solicitação de Compras, itens e fornecedores (cadastro rápido via `busca_cnpj`) e, ao submeter, gera os Orçamentos de Fornecedor submetidos e as Ordens de Compra em rascunho dos itens confirmados, datadas pela confirmação no Bionexo. Botão *Importar PDF Bionexo* na Request for Quotation e card *Bionexo* no workspace Compras.
- **Vencedores:** janela de confirmação ao concluir (padrão: orçamentos só dos itens confirmados e dos fornecedores vencedores; caixa *Gerar também orçamentos dos demais fornecedores*, marcada, inclui os demais com todos os itens cotados).
- **RFQ gerada:** Solicitação de Compras sem Pedido de Cotação gera o Pedido de Cotação a partir do relatório (cancelado junto com a importação).
- Seção *Vínculo* renomeada para *Referências*; Empresa editável e preenchida pela referência; filtro de itens do formulário é consulta no servidor (nome e quantidade) e a pendência indica itens que existem no ERP mas não na Solicitação/Pedido.

## v1.17.2 — Mínimo de 10 variantes e e-mail institucional · 2026-10-25

- Modelo WhatsApp ativo só salva com ao menos 10 variantes ativas (`roteador.MIN_VARIANTES`); modelo criado por código recebe as redações-semente do título (`seed/variantes_modelos.py`) e o patch `completar_variantes_modelo_whatsapp` completa os existentes (os sem semente ficam no Error Log). Boas-vindas e Tarefa ganham 10 variantes (patch `completar_variantes_boas_vindas_tarefa`). Notification com "Enviar também por WhatsApp" passa a exigir o Modelo WhatsApp.
- **E-mail no layout institucional** (manifesto do clm, seção 6): e-mails das Notifications com canal E-mail, do Modelo WhatsApp (canal E-mail ou fallback) e do avanço de etapa do Edital saem pelo `render_email` do clm (`email_institucional.py`, dependência fraca).

## v1.17.1 — WhatsApp: anexo do formato de impressão · 2026-10-22

- Na Notification, "Attach Print" + "Print Format" também valem para o WhatsApp: o PDF é gerado no envio (`frappe.attach_print`, mesmas travas de rascunho/cancelado do e-mail) e enviado como documento por `sendMedia`, com o texto como legenda. Limite de 15 MB; `Envio WhatsApp` registra formato e nome do arquivo.
- Hook `whatsapp_contexto_extra` e ajuda de helpers no Modelo WhatsApp.

## v1.17.0 — WhatsApp: roteamento entre instâncias · 2026-10-20

- A tabela "Instâncias adicionais" em Configuracoes WhatsApp (peso e limite diário opcionais) soma-se à instância principal; `whatsapp/distribuidor.py` envia cada mensagem pela conectada de menor carga do dia, com afinidade por destinatário e failover. Sem linhas adicionais o comportamento não muda. A instância usada fica em `Envio WhatsApp`; criar instância e gerar QR Code escolhem a instância.
- "Criar instância" informa se a instância foi criada ou já existia, trata 404 na consulta e mostra o corpo do erro HTTP da Evolution (também no Error Log).

## v1.16.2 — WhatsApp: variantes-semente · 2026-10-20

- Modelos WhatsApp sem variantes recebem as redações-semente (patch `semear_variantes_modelo_whatsapp`).

## v1.16.1 — Políticas de acesso · 2026-10-20

- `politicas/acesso_doctypes.py`: a cada migrate, avisa sobre DocTypes órfãos ou inalcançáveis (teste `test_politica_acesso`). Atalho de Assunto Judicial.

## v1.16.0 — WhatsApp: variantes de mensagem · 2026-10-20

- `Modelo WhatsApp` aceita redações alternativas (tabela `variantes`) e o roteador (`whatsapp/roteador.py`) sorteia uma por destinatário, sem repetir a anterior nem a última recebida pelo mesmo número; função Jinja `sorteio("Oi","Olá")`. A variante usada fica em `Envio WhatsApp`; interruptor "Variar mensagens" em Configuracoes WhatsApp.

## v1.15.0 — WhatsApp: Modelo dedicado e destinatários sem User · 2026-10-17

- Modelo WhatsApp dedicado por notificação e normalização de número pelo conector.
- Destinatários sem User: campos Phone do documento (inclusive de tabelas filhas) escolhidos na tabela Recipients e o campo "Números WhatsApp adicionais" (um por linha, aceita Jinja) geram Envio WhatsApp sem usuário; números repetidos recebem uma só mensagem.

## v1.14.0 — WhatsApp: conector da Evolution API v2 · 2026-10-14

- Conector estável (`whatsapp/conector.py`: `estado_conexao`, `verificar_numero`, `enviar_texto`, `normalizar_numero_br`) com espaçamento entre envios, timeouts configuráveis e sem retry em envio; novos campos em Configuracoes WhatsApp (ativo, timeouts, intervalo, verificação prévia, webhook reservado).
- Envio de documento (PDF) pelo conector. Preparados o hook `evolution_webhook_handlers` e o endpoint de webhook, ainda desligado (HTTP 501).

## v1.11.0 — mudanças desde v1.10.0

- **Jurídico:** anexo por movimentação com coluna visível na tabela do processo, descrição composta a partir dos complementos tabelados e leitura de submovimentos; anexos existentes são preservados nas atualizações do DataJud.
- **Partes:** opção Terceiros vinculada a Contatos para cadastro de pacientes, também disponível no filtro da Relação de Processos.

## v1.10.0 — mudanças desde v1.5.4

- **v1.6.0 — Integração judicial:** criação do módulo Jurídico, do Workspace, dos DocTypes Processo Judicial, Assunto Judicial, Configurações DataJud, assuntos e movimentos; consulta ao DataJud por número CNJ e tribunal, registro dos dados e migrações de cadastro e permissões.
- **v1.7.0 — Cadastro e acompanhamento:** cadastro em rascunho ou concluído, vinculação de empresa e parte, classificação de fase, risco e situação, proteção dos dados recebidos do DataJud, atualização periódica de processos em andamento e testes do fluxo judicial.
- **v1.8.0 — Consulta manual e conexões:** busca manual de andamentos, vínculos de processos com colaboradores, clientes, fornecedores e processos relacionados, com acesso pelas respectivas telas.
- **v1.9.0 — Indicadores:** Dashboard View “Processos Judiciais” com três cartões numéricos e seis gráficos de situação, risco, fase, tribunal, localidade IBGE e assuntos frequentes; reorganização do Workspace Jurídico.
- **v1.10.0 — Relatório:** “Relação de Processos” com filtros por empresa, tipo e nome da parte, fase, situação, situação cadastral, assunto, tribunal, grau, risco, número e período de ajuizamento. Inclui os principais dados cadastrados, impressão e PDF em formato próprio com o letter-head padrão do Frappe e link na caixa Relatórios do Workspace.
