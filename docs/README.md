# Contencioso / Processos Judiciais — Módulo (PT-BR)

## Visão Geral
Este módulo adiciona ao ERPNext/Frappe funcionalidades para gestão de **processos judiciais**, com foco em **trabalhista**, integrando:
- cadastro estruturado do processo (CNJ, tribunal, fase/status)
- partes (tipo + nome dinâmico) e papel no processo
- eventos/movimentações (linha do tempo)
- prazos/obrigações com alertas
- audiências
- documentos e peças (anexos) com confidencialidade
- risco/exposição/provisão com histórico (snapshots)
- financeiro do contencioso (custas, honorários, depósitos, acordos etc.)
- segurança por **RBAC** + **nível de sigilo**
- relatórios e dashboards (executivo e jurídico)
- preparação para integrações (stub, sem chamadas externas na Fase 1)

## Onde fica no código
Submódulo dentro do app:
- `integracoes_customizadas/contencioso/`

## DocTypes principais
- **Processo Judicial**
  - Estado do workflow em `cj_estado_workflow` (campo técnico exigido pelo Frappe)
- Child Tables:
  - CJ Parte (com `tipo_da_parte` + `nome_da_parte` Dynamic Link)
  - CJ Evento
  - CJ Prazo
  - CJ Audiencia
  - CJ Documento
  - CJ Item Financeiro
  - CJ Snapshot de Risco
  - CJ Integracao (Stub)

## Série de Nomenclatura
- Processo Judicial: `ProcJud-.YYYY.-.#####`

## Como usar (fluxo mínimo)
1) Crie um **Processo Judicial** preenchendo:
   - CNJ, Company, responsável, tipo/fase/status
2) Adicione **Partes**:
   - Tipo da Parte (Customer/Supplier/Employee)
   - Nome da Parte (Dynamic Link)
   - Papel (Reclamante/Reclamada)
3) Registre **Eventos** e **Prazos**
4) Cadastre **Audiências** e anexe **Atas**
5) Anexe **Documentos/Peças**
6) Atualize **Risco/Provisão** e registre snapshots quando houver mudança
7) Registre **Itens Financeiros** e comprovantes
8) Use relatórios e dashboards para governança e acompanhamento

## Segurança e Sigilo
- Campo do processo: `cj_nivel_sigilo` (Publico/Restrito/Sigiloso)
- Documentos podem ser marcados como `cj_confidencial`
- Regras detalhadas em `docs/SEGURANCA.md`

## Relatórios e Dashboards
Detalhados em `docs/RELATORIOS_DASHBOARDS.md`.
Dashboards criados:
- Dashboard Executivo
- Dashboard Jurídico

## Integrações (Stub)
Estrutura e logs preparados em `docs/INTEGRACOES_STUB.md`.
Na Fase 1, não há chamadas externas.

## Testes
Ver `docs/PLANO_TESTES.md`.

## Instalação/Upgrade
Ver `docs/INSTALACAO.md`.
