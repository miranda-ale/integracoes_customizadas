# DataJud: structured logs, circuit breaker and queue isolation

## Original problem

The DataJud Public API (CNJ) started answering HTTP 403 `security_exception ... unauthorized for API key` on every
court, including with the official public key published on the CNJ wiki. Two symptoms before this change:

1. The Error Log only recorded `"Processo X, tribunal Y: DataJudError. Dados anteriores preservados."` (lawsuit X,
   court Y: DataJudError, previous data preserved), with no endpoint, HTTP status, response body or traceback --
   impossible to diagnose remotely.
2. Each followed lawsuit became its own task on the `long` RQ queue, the same queue as
   `rh_brasil.dossier.run_dossier` (Generate Employee Dossier). With the API down, dozens of DataJud tasks piled up
   and failed one by one, delaying the dossier (the user saw "Generating the dossier..." indefinitely).

## Structured and grouped log

Every API call goes through `_post` (`juridico/datajud.py`), which measures response time, classifies the failure and
writes a **DataJud Sync Log**:

| Field | Content |
| --- | --- |
| `execucao` | Start of the run (groups several failures of the same round) |
| `tipo_erro` | `Autenticação` (401/403) · `Limite de Requisições` (429) · `Não Encontrado` (404) · `Indisponível` (5xx/timeout/connection) · `Dados Inválidos` (JSON/unexpected body) |
| `contagem` / `processos_afetados` | One record per run and error type, not per lawsuit -- see `_ColetorErros` |
| `tribunal`, `indice`, `numero_processo`, `endpoint`, `metodo`, `status_http`, `tempo_resposta_ms` | From the most recent occurrence of that error type in the run |
| `corpo_resposta` | First 1,000 characters of the response body |
| `tipo_excecao`, `traceback` | When the failure came from a Python exception (timeout, connection) |
| `api_key_mascarada` | Only the first 4 characters of the key (`_mascarar_chave`); the full `Authorization` header is never written |

An **interactive** call (`acompanhar_processo`, `buscar_andamentos`, triggered by the user in the Desk) writes
immediately, with `contagem=1`. The **batch** synchronization (see below) accumulates everything in an
`_ColetorErros` and writes only at the end of the run -- so never more than one record per error type and run, even
with 56 lawsuits failing at the same time.

`DataJud Settings` summarizes the state in its own fields (`ultima_sincronizacao_sucesso`, `ultimo_erro`,
`ultimo_erro_status_http`, `falhas_consecutivas`), without needing to open the Error Log.

## Circuit breaker

`DataJud Settings` also holds the circuit state (`circuito_aberto`, `circuito_tipo_falha`, `circuito_motivo`,
`circuito_aberto_em`, `circuito_nivel_backoff`, `circuito_proxima_tentativa`):

- It opens after consecutive failures of the same type: 3 of `Autenticação` or 5 of `Limite de Requisições`/`Indisponível`
  (`LIMITE_FALHAS_CIRCUITO`). A failure of a different type restarts the count.
- **Authentication**: does not retry by itself -- only changing the key in `DataJud Settings` reopens the circuit
  (`DataJudSettings.validate()` detects `has_value_changed("api_key")` and resets the circuit fields).
- **Rate limit / Unavailable**: reopens by itself with exponential backoff (`BACKOFF_INICIAL_MINUTOS = 15`, doubling
  on each failure up to `BACKOFF_MAXIMO_MINUTOS = 240`).
- Opening or closing the circuit notifies the `System Manager` users by e-mail (`_notificar_administradores`).
- Before processing any lawsuit, `sincronizar_processos_acompanhados` runs a health check (`_verificar_saude`, a
  `size=1` query on a stable court). If it fails, the whole run is aborted without trying any lawsuit.

## Single batch, dedicated queue and time budget

- The cron (`agendar_sincronizacao`, Mon-Fri 3 a.m.) enqueues **a single task**
  (`sincronizar_processos_acompanhados`), never one per lawsuit anymore -- it uses a fixed `job_id`
  (`JOB_ID_LOTE`) with `deduplicate=True`, so repeated triggers (cron + manual trigger) do not pile up.
- That task runs on the **`datajud`** queue (`FILA_LOTE`), no longer on `long`: the synchronization never competes
  with the employee dossier or other interactive tasks for the same worker. **A bench that installs this app needs
  its own worker listening on the `datajud` queue** (`bench worker --queue datajud`, or the equivalent entry in the
  bench supervisor/Procfile) -- this is infrastructure configuration, outside the scope of this app repository.
- Each request uses a short timeout (`TIMEOUT_LOTE = (5, 12)` seconds) and no retry (`tentativas=1`); the whole run
  respects a total budget (`ORCAMENTO_LOTE_SEGUNDOS = 20 min`) -- leftover lawsuits wait for the next cron window
  instead of locking up the worker.

## Tests

`juridico/test_datajud.py` simulates 200, 403, 429, 500, timeout and 404 by mocking `requests.post` (no real network
call), and covers key masking, the grouping of `_ColetorErros` and the opening/closing of the circuit breaker,
including the automatic reopening when the key is changed.

See also [ADR-002](adr-002-log-quality-and-readability.md) for the general principle behind this design.
