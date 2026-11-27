# DataJud: logs estruturados, circuit breaker e isolamento de fila

## Problema original

A API Pública do DataJud (CNJ) passou a responder HTTP 403 `security_exception ... unauthorized for API key`
em todos os tribunais, inclusive com a chave pública oficial publicada na wiki do CNJ. Dois sintomas antes desta
mudança:

1. O Error Log só gravava `"Processo X, tribunal Y: DataJudError. Dados anteriores preservados."`, sem endpoint,
   status HTTP, corpo da resposta nem traceback — impossível diagnosticar à distância.
2. Cada processo acompanhado virava uma tarefa própria na fila RQ `long`, a mesma fila de `rh_brasil.dossier.run_dossier`
   (Gerar Dossiê do Colaborador). Com a API fora do ar, dezenas de tarefas DataJud se acumulavam e falhavam uma a
   uma, atrasando o dossiê (o usuário via "Gerando o dossiê..." por tempo indefinido).

## Log estruturado e agrupado

Toda chamada à API passa por `_post` (`juridico/datajud.py`), que mede tempo de resposta, classifica a falha e
grava um **DataJud Sync Log**:

| Campo | Conteúdo |
| --- | --- |
| `execucao` | Início da execução (agrupa várias falhas da mesma rodada) |
| `tipo_erro` | `Autenticação` (401/403) · `Limite de Requisições` (429) · `Não Encontrado` (404) · `Indisponível` (5xx/timeout/conexão) · `Dados Inválidos` (JSON/corpo inesperado) |
| `contagem` / `processos_afetados` | Um registro por execução e tipo de erro, não por processo — ver `_ColetorErros` |
| `tribunal`, `indice`, `numero_processo`, `endpoint`, `metodo`, `status_http`, `tempo_resposta_ms` | Da ocorrência mais recente desse tipo de erro na execução |
| `corpo_resposta` | Primeiros 1.000 caracteres do corpo da resposta |
| `tipo_excecao`, `traceback` | Quando a falha veio de uma exceção Python (timeout, conexão) |
| `api_key_mascarada` | Só os 4 primeiros caracteres da chave (`_mascarar_chave`); o header `Authorization` completo nunca é gravado |

Uma chamada **interativa** (`acompanhar_processo`, `buscar_andamentos`, disparadas pelo usuário no Desk) grava na
hora, com `contagem=1`. A sincronização **em lote** (ver abaixo) acumula tudo num `_ColetorErros` e grava só ao
final da execução — por isso nunca mais de um registro por tipo de erro e execução, mesmo com 56 processos
falhando ao mesmo tempo.

`Configurações DataJud` resume o estado em campos próprios (`ultima_sincronizacao_sucesso`, `ultimo_erro`,
`ultimo_erro_status_http`, `falhas_consecutivas`), sem precisar abrir o Error Log.

## Circuit breaker

`Configurações DataJud` também guarda o estado do circuito (`circuito_aberto`, `circuito_tipo_falha`,
`circuito_motivo`, `circuito_aberto_em`, `circuito_nivel_backoff`, `circuito_proxima_tentativa`):

- Abre depois de falhas seguidas do mesmo tipo: 3 de `Autenticação` ou 5 de `Limite de Requisições`/`Indisponível`
  (`LIMITE_FALHAS_CIRCUITO`). Uma falha de tipo diferente reinicia a contagem.
- **Autenticação**: não tenta de novo sozinho — só a troca da chave em `Configurações DataJud` reabre o circuito
  (`ConfiguraçõesDataJud.validate()` detecta `has_value_changed("api_key")` e reseta os campos do circuito).
- **Limite de requisições / Indisponível**: reabre sozinho com backoff exponencial (`BACKOFF_INICIAL_MINUTOS = 15`,
  dobrando a cada falha até `BACKOFF_MAXIMO_MINUTOS = 240`).
- Abrir ou fechar o circuito notifica os `System Manager` por e-mail (`_notificar_administradores`).
- Antes de processar qualquer processo, `sincronizar_processos_acompanhados` faz um health check (`_verificar_saude`,
  consulta `size=1` num tribunal estável). Se falhar, a execução inteira é abortada sem tentar nenhum processo.

## Lote único, fila dedicada e orçamento de tempo

- O cron (`agendar_sincronizacao`, seg-sex 3h) enfileira **uma única tarefa** (`sincronizar_processos_acompanhados`),
  nunca mais uma por processo — usa `job_id` fixo (`JOB_ID_LOTE`) com `deduplicate=True`, então disparos repetidos
  (cron + acionamento manual) não se acumulam.
- Essa tarefa roda na fila **`datajud`** (`FILA_LOTE`), não mais em `long`: a sincronização nunca mais compete
  com o dossiê do colaborador ou outras tarefas interativas pelo mesmo worker. **Uma bench que instala este app
  precisa de um worker próprio escutando a fila `datajud`** (`bench worker --queue datajud`, ou a entrada
  equivalente no supervisor/Procfile da bench) — isso é configuração de infraestrutura, fora do escopo deste
  repositório de app.
- Cada requisição usa timeout curto (`TIMEOUT_LOTE = (5, 12)` segundos) e sem retentativa (`tentativas=1`); a
  execução inteira respeita um orçamento total (`ORCAMENTO_LOTE_SEGUNDOS = 20 min`) — processos que sobrarem ficam
  para a próxima janela do cron, em vez de travar o worker.

## Testes

`juridico/test_datajud.py` simula 200, 403, 429, 500, timeout e 404 mockando `requests.post` (nenhuma chamada de
rede real), cobre o mascaramento da chave, o agrupamento do `_ColetorErros` e a abertura/fechamento do circuit
breaker, inclusive a reabertura automática ao trocar a chave.

Ver também [ADR-002](adr-002-qualidade-e-legibilidade-de-logs.md) para o princípio geral por trás deste desenho.
