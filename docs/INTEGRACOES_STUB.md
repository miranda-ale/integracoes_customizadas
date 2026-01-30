# Integrações (Stub) — Contencioso (PT-BR)

## Objetivo
Preparar a estrutura para integrações externas (ex.: DataJud/CNJ e provedores) **sem depender de rede** na Fase 1.

## Requisitos (Fase 1)
- Child table `CJ Integracao (Stub)`:
  - provedor, chave externa, última sync, status, log
- Idempotência (planejada):
  - eventos importados devem armazenar `cj_id_externo` (quando houver)
  - evitar duplicação de eventos ao sincronizar
- Scheduler:
  - job **desativado por padrão**
  - se ativado, roda em background e registra logs
  - não deve quebrar o site (fail-safe)

## Implementação sugerida (estrutura)
Criar pasta:
- `integracoes_customizadas/contencioso/integracoes/`

Arquivo implementado:
- `stub.py` (entrypoint `executar_sync_stub`)

Assinaturas sugeridas:
- `sync_processo(processo_name: str) -> None`
  - se integração desativada: registra "Integração desativada (stub)" em `cj_log_sync`
  - não faz chamadas externas

## Configuração
- A execução do stub fica desativada por padrão.
- Para ativar em ambiente controlado, definir `contencioso_integracao_ativa = true` em `site_config.json`.

## Integração Datajud (API Pública CNJ)

Para consultar processos pelo número CNJ no formulário de Processo Judicial, é necessária a **chave da API Datajud**, obtida no portal do Datajud/CNJ. Configure em `site_config.json`:

- `datajud_api_key`: chave pública da API Datajud (não versionar).
- `contencioso_integracao_ativa`: `true` para habilitar a busca.

Documentação detalhada: [DATAJUD.md](DATAJUD.md).

## Logging
- O stub usa logger `contencioso` e registra a execução com timestamp.
- Logs por processo podem ser ampliados na Fase 2 via `cj_log_sync`.
