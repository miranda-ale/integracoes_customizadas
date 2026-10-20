# Histórico de alterações

## Não lançado

- **WhatsApp:** variantes de mensagem. `Modelo WhatsApp` aceita redações alternativas (tabela `variantes`) e o roteador (`whatsapp/roteador.py`) sorteia uma por destinatário, sem repetir a anterior nem a última recebida pelo mesmo número; função Jinja `sorteio("Oi","Olá")` para variar trechos. A variante usada fica em `Envio WhatsApp`; o interruptor é "Variar mensagens" em Configuracoes WhatsApp.
- **WhatsApp nas Notifications:** destinatários sem User. Campos Phone do documento (inclusive de tabelas filhas) escolhidos na tabela Recipients e o novo campo "Números WhatsApp adicionais" (um por linha, aceita Jinja) geram Envio WhatsApp sem usuário; números repetidos recebem uma só mensagem.
- **WhatsApp:** conector estável da Evolution API v2 (`whatsapp/conector.py`: `estado_conexao`, `verificar_numero`, `enviar_texto`, `normalizar_numero_br`) com espaçamento entre envios, timeouts configuráveis e sem retry em envio; novos campos em Configuracoes WhatsApp (ativo, timeouts, intervalo, verificação prévia, webhook reservado). Preparado o hook `evolution_webhook_handlers` e o endpoint de webhook, ainda desligado (HTTP 501).

## v1.11.0 — mudanças desde v1.10.0

- **Jurídico:** anexo por movimentação com coluna visível na tabela do processo, descrição composta a partir dos complementos tabelados e leitura de submovimentos; anexos existentes são preservados nas atualizações do DataJud.
- **Partes:** opção Terceiros vinculada a Contatos para cadastro de pacientes, também disponível no filtro da Relação de Processos.

## v1.10.0 — mudanças desde v1.5.4

- **v1.6.0 — Integração judicial:** criação do módulo Jurídico, do Workspace, dos DocTypes Processo Judicial, Assunto Judicial, Configurações DataJud, assuntos e movimentos; consulta ao DataJud por número CNJ e tribunal, registro dos dados e migrações de cadastro e permissões.
- **v1.7.0 — Cadastro e acompanhamento:** cadastro em rascunho ou concluído, vinculação de empresa e parte, classificação de fase, risco e situação, proteção dos dados recebidos do DataJud, atualização periódica de processos em andamento e testes do fluxo judicial.
- **v1.8.0 — Consulta manual e conexões:** busca manual de andamentos, vínculos de processos com colaboradores, clientes, fornecedores e processos relacionados, com acesso pelas respectivas telas.
- **v1.9.0 — Indicadores:** Dashboard View “Processos Judiciais” com três cartões numéricos e seis gráficos de situação, risco, fase, tribunal, localidade IBGE e assuntos frequentes; reorganização do Workspace Jurídico.
- **v1.10.0 — Relatório:** “Relação de Processos” com filtros por empresa, tipo e nome da parte, fase, situação, situação cadastral, assunto, tribunal, grau, risco, número e período de ajuizamento. Inclui os principais dados cadastrados, impressão e PDF em formato próprio com o letter-head padrão do Frappe e link na caixa Relatórios do Workspace.
