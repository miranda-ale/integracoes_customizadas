# PRD — Módulo de Contencioso / Processos Judiciais (PT-BR)

## 1. Objetivo
Implementar no ERPNext/Frappe um módulo para gestão de processos judiciais, com foco em trabalhista, permitindo:
- acompanhamento técnico (Jurídico)
- visão executiva (Gestão)
- rastreabilidade e automação (Engenharia)
- governança, segurança e LGPD

## 2. Personas e necessidades
### 2.1 Gestor (Diretoria/Coordenação)
- visão consolidada por unidade/centro de custo
- exposição, provisão, tendência e custo
- prazos críticos e risco

### 2.2 Jurídico (Advocacia corporativa)
- linha do tempo completa
- prazos, audiências, peças e evidências
- estratégia, tese e resultado (incluindo acordos)
- controle de sigilo

### 2.3 Backoffice (Financeiro/DP/SST/Qualidade)
- pagamentos (custas, honorários, acordos)
- evidências e documentos necessários
- lições aprendidas e ações preventivas (quando aplicável)

## 3. Escopo (Fase 1)
Inclui:
- Cadastro do Processo Judicial com CNJ e Naming Series `ProcJud-.YYYY.-.#####`
- Partes do processo (com “tipo” + “nome” dinâmico) e representantes (mínimo viável)
- Eventos/movimentações (linha do tempo)
- Prazos/obrigações com alertas e escalonamento
- Audiências
- Documentos e peças (anexos) com marcação de confidencialidade
- Risco, exposição e provisão com histórico (snapshot)
- Financeiro do contencioso (itens e anexos)
- Workflows e permissões (RBAC + sigilo)
- Relatórios e dashboards mínimos
- Integrações apenas como **stub** (modelo + logs + scheduler desativado)

Não inclui na Fase 1:
- Integração real com DataJud/CNJ ou provedores externos
- Cálculo automático de prazos por calendário forense
- Geração automática de peças

## 4. Requisitos funcionais (RF)
- RF01: Criar, editar e consultar Processo Judicial com CNJ único.
- RF02: Vincular processo a Company e (opcional) a Employee (ex-colaborador).
- RF03: Registrar partes com chaveamento (tipo da parte + nome dinâmico) e papel no processo.
- RF04: Registrar eventos/movimentações com origem (manual/integração).
- RF05: Criar prazos com escalonamento de alertas (D-10/D-5/D-1 e vencido).
- RF06: Registrar audiências (data, modalidade, participantes, resultado, ata).
- RF07: Anexar documentos/peças com categoria e confidencialidade.
- RF08: Registrar risco, exposição e provisão e manter histórico de snapshots.
- RF09: Registrar itens financeiros (custas, honorários, depósitos, acordos, condenações).
- RF10: Relatórios e dashboards mínimos (executivo e jurídico).
- RF11: Segurança por nível de sigilo e RBAC.
- RF12: Logs e estrutura para integração (stub), com idempotência planejada.

## 5. Requisitos não funcionais (RNF)
- RNF01: Auditoria: histórico de alterações (Frappe) e Versioning quando aplicável.
- RNF02: Segurança: RBAC + sigilo do processo + restrição de anexos confidenciais.
- RNF03: Desempenho: listagens com filtros e índices quando necessário.
- RNF04: Idempotência (integração): eventos importados não podem duplicar.
- RNF05: Documentação completa em Markdown.
- RNF06: Testes mínimos e checklist de QA.

## 6. Definição de pronto (DoD) global
- DocTypes e workflows criados e revisados.
- Permissões testadas com usuários por role.
- Relatórios e dashboards funcionando com dados de exemplo.
- Notificações de prazos funcionando (incluindo escalonamento).
- Documentação completa em `docs/`.
- Submódulo instalável/atualizável via bench.
