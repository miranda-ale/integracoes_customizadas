# Modelo de Dados — Contencioso / Processos Judiciais (PT-BR)

## Convenções
- Campos em `snake_case`
- Prefixo `cj_` para campos específicos do módulo
- DocTypes e labels em português
- Preferir Link para DocTypes nativos quando aplicável: `Company`, `Employee`, `Supplier`, `Customer`, `User`, `Contact`, `Project`, `Cost Center`
- Listas repetidas devem ser **Child Tables** (Table)

---

## 1) DocType: Processo Judicial
### Série de Nomenclatura (Naming)
- `naming_series`: `ProcJud-.YYYY.-.#####`

### Identificação do Processo
- `cj_numero_cnj` (Data, **Unique**, obrigatório)
- `cj_titulo` (Data, obrigatório) — ex.: "Reclamação Trabalhista - Fulano"
- `cj_tipo_processo` (Select): Trabalhista, Cível, Consumidor, Fiscal, Outros
- `cj_sistema_justica` (Select): JT, JE, JF, TJ, TRF, Outros
- `cj_tribunal` (Data) — ex.: TRT-2, TJSP
- `cj_vara_foro` (Data) — vara/foro
- `cj_classe` (Data) — Fase 1: texto; futuro: tabela CNJ
- `cj_assuntos` (Small Text) — Fase 1: texto; futuro: tabela CNJ
- `cj_data_distribuicao` (Date)
- `cj_ultima_movimentacao_em` (Datetime, read-only)

### Status e Fase
- `cj_status` (Select): Ativo, Suspenso, Arquivado, Encerrado
- `cj_fase` (Select): Inicial, Instrução, Sentença, Recursos, Execução, Encerrado
- `cj_resultado_final` (Select, opcional na Fase 1): Procedente, Parcialmente Procedente, Improcedente, Acordo, Extinção, Outro
- `cj_data_encerramento` (Date)

### Gestão
- `company` (Link -> Company, obrigatório)
- `cost_center` (Link -> Cost Center, opcional)
- `project` (Link -> Project, opcional)
- `cj_area_negocio` (Select): RH/DP, SST, Operações, Financeiro, Outros
- `cj_responsavel_usuario` (Link -> User, obrigatório)
- `cj_escritorio_externo` (Link -> Supplier, opcional) — escritório de advocacia
- `cj_nivel_sigilo` (Select): Publico, Restrito, Sigiloso

### Trabalhista (quando aplicável)
- `cj_empregado_relacionado` (Link -> Employee, opcional)
- `cj_data_inicio_vinculo` (Date, opcional)
- `cj_data_fim_vinculo` (Date, opcional)
- `cj_cargo_epoca` (Data, opcional)
- `cj_unidade_lotacao` (Data, opcional)
- `cj_tipos_pedidos` (Small Text) — Fase 1: texto estruturado
- `cj_periodo_controverso_inicio` (Date, opcional)
- `cj_periodo_controverso_fim` (Date, opcional)

### Risco e Valores (Snapshot Atual)
- `cj_probabilidade_perda` (Select): Remota, Possível, Provável
- `cj_valor_pedido` (Currency)
- `cj_valor_estimado` (Currency)
- `cj_melhor_cenario` (Currency)
- `cj_pior_cenario` (Currency)
- `cj_provisao_atual` (Currency)
- `cj_base_provisao` (Small Text)

### Child Tables (Tabelas Filhas)
- `cj_partes` (Table -> **CJ Parte**)
- `cj_eventos` (Table -> **CJ Evento**)
- `cj_prazos` (Table -> **CJ Prazo**)
- `cj_audiencias` (Table -> **CJ Audiencia**)
- `cj_documentos` (Table -> **CJ Documento**)
- `cj_itens_financeiros` (Table -> **CJ Item Financeiro**)
- `cj_historico_risco` (Table -> **CJ Snapshot de Risco**)
- `cj_integracoes` (Table -> **CJ Integracao (Stub)**)

---

## 2) Child DocType: CJ Parte
### Requisito especial (chaveamento)
- `tipo_da_parte` (Select) — opções exatas: **Customer**, **Supplier**, **Employee** — default: **Employee**
- `nome_da_parte` (**Dynamic Link**) — `options` aponta para `tipo_da_parte`

### Campos adicionais
- `cj_papel_parte` (Select): Reclamante, Reclamada, Terceiro, Ministério Público, Outros
- `cj_contato` (Link -> Contact, opcional)
- `cj_observacoes` (Small Text)

> Observação técnica: `nome_da_parte` deve ser do tipo **Dynamic Link** para alternar entre Customer/Supplier/Employee.

---

## 3) Child DocType: CJ Evento
- `cj_data_hora` (Datetime, obrigatório)
- `cj_origem` (Select): Manual, Integração
- `cj_tipo_evento` (Select): Movimento, Publicação, Despacho, Sentença, Audiência, Documento, Outro
- `cj_resumo` (Data, obrigatório)
- `cj_detalhes` (Long Text)
- `cj_id_externo` (Data, opcional) — idempotência
- `cj_gera_prazo` (Check)
- `cj_referencia_prazo` (Data/Link, opcional) — decisão técnica a documentar

> Decisão técnica (Fase 1): implementado como **Data** para referência livre. Quando houver DocType específico de prazos, pode ser migrado para Link.

---

## 4) Child DocType: CJ Prazo
- `cj_tipo_prazo` (Select): Contestação, Recurso, Manifestação, Custas, Documentos, Outro
- `cj_data_inicio` (Date)
- `cj_data_vencimento` (Date, obrigatório)
- `cj_responsavel_usuario` (Link -> User)
- `cj_status_prazo` (Select): A Vencer, Vencido, Cumprido, Cancelado
- `cj_checklist` (Small Text)
- `cj_concluido_em` (Datetime)
- `cj_observacao_conclusao` (Small Text)

---

## 5) Child DocType: CJ Audiencia
- `cj_data_hora` (Datetime, obrigatório)
- `cj_modalidade` (Select): Presencial, Telepresencial
- `cj_local` (Data)
- `cj_link` (Data)
- `cj_participantes` (Small Text)
- `cj_resultado` (Select): Sem acordo, Acordo, Adiada, Instrução, Outro
- `cj_ata` (Attach)

---

## 6) Child DocType: CJ Documento
- `cj_categoria` (Select): Inicial, Contestação, Recurso, Procuração, Cálculos, Acordo, Sentença, Ata, Outro
- `cj_titulo` (Data)
- `cj_arquivo` (Attach, obrigatório)
- `cj_versao` (Data, opcional)
- `cj_observacoes` (Small Text)
- `cj_confidencial` (Check)

---

## 7) Child DocType: CJ Item Financeiro
- `cj_tipo` (Select): Custas, Depósito Recursal, Honorários, Perícia, Acordo, Condenação, Outro
- `cj_data` (Date, obrigatório)
- `cj_valor` (Currency, obrigatório)
- `cj_favorecido` (Data, opcional) — (futuro: Link configurável)
- `cj_referencia` (Data)
- `cj_observacoes` (Small Text)
- `cj_payment_entry` (Link -> Payment Entry, opcional)
- `cj_comprovante` (Attach, opcional)

---

## 8) Child DocType: CJ Snapshot de Risco
- `cj_data_hora_snapshot` (Datetime, obrigatório)
- `cj_probabilidade_perda` (Select): Remota, Possível, Provável
- `cj_valor_estimado` (Currency)
- `cj_provisao` (Currency)
- `cj_base` (Small Text)
- `cj_usuario` (Link -> User)

---

## 9) Child DocType: CJ Integracao (Stub)
- `cj_provedor` (Select): DataJud, Jusbrasil, Outro
- `cj_chave_externa` (Data)
- `cj_ultima_sync_em` (Datetime)
- `cj_status_sync` (Select): Disabled, OK, Error
- `cj_log_sync` (Long Text)
