# Plano de Testes — Contencioso (PT-BR)

## 1) Testes Unitários (mínimo)
- Criação de Processo Judicial:
  - `cj_numero_cnj` obrigatório e único
  - `company` obrigatório
  - naming series funcionando (`ProcJud-...`)
- Partes do processo:
  - `tipo_da_parte` default = Employee
  - `nome_da_parte` (Dynamic Link) respeita `tipo_da_parte`
- Prazos:
  - `cj_data_vencimento` obrigatório
  - alteração de status para Cumprido preenche `cj_concluido_em`
- Encerramento via workflow:
  - exigir `cj_resultado_final` e `cj_data_encerramento`
  - exigir documento "Sentença" ou "Acordo" (mínimo 1)

## 2) Testes de Integração (mínimo)
### Permissões e Sigilo
- Visualizador Executivo:
  - não visualiza processos `cj_nivel_sigilo = Sigiloso`
  - relatórios mostram apenas agregados, sem detalhes sensíveis
- CJ Analista Jurídico:
  - visualiza processos Publico e Restrito
  - não visualiza Sigiloso (se a política assim definir), a menos que também tenha role superior
- CJ Gestor Jurídico:
  - visualiza tudo, inclusive Sigiloso

### Anexos confidenciais
- Documento com `cj_confidencial = 1`:
  - não deve ser exposto para roles não jurídicas

### Notificações
- Prazos D-10/D-5/D-1: notificação in-app enviada ao responsável do prazo.
- Prazos vencidos: notificação ao mudar status para "Vencido".

### Dashboards
- Dashboard Executivo: KPIs calculados sem incluir processos Sigilosos.
- Dashboard Jurídico: KPIs de prazos e audiências respeitam sigilo.

## 3) Scheduler (quando ativado)
- Job marca prazos como Vencido quando `cj_data_vencimento < hoje` e status era "A Vencer".
- Job de stub de integração não faz chamadas externas e apenas escreve log.

## 4) Dados de exemplo (para QA manual)
- 3 processos:
  - 1 Público, 1 Restrito, 1 Sigiloso
- 2 prazos por processo:
  - 1 a vencer, 1 vencido
- 1 audiência futura em pelo menos 1 processo
- 2 eventos por processo
- Itens financeiros em 2 processos
