# Módulo de Provas e Gestão de Processos Seletivos

**Versão:** 0.1.0  
**App:** integracoes_customizadas  
**Módulo:** Provas

## Visão Geral

O módulo de Provas é uma extensão para o ERPNext/HRMS que permite a gestão completa de processos seletivos, incluindo:

- Banco de questões organizado por disciplinas
- Geração automática de provas
- Gestão de editais de processos seletivos
- Acompanhamento de candidatos por etapas
- Relatórios gerenciais
- Integração com os DocTypes padrão do HRMS (Job Applicant, Job Opening, Interview, Interview Round)

---

## DocTypes

### 1. Disciplina

Categoriza as questões por área de conhecimento.

**Campos principais:**
- `titulo`: Nome da disciplina
- `aplicavel_a_todos`: Se marcado, questões desta disciplina podem ser aplicadas a qualquer cargo
- `designations`: Lista de cargos aos quais a disciplina se aplica (quando não aplicável a todos)

---

### 2. Questão

Banco de questões para composição das provas.

**Campos principais:**
- `enunciado`: Texto da questão
- `disciplina`: Link para Disciplina
- `nivel_dificuldade`: Fácil, Médio ou Difícil
- `designations`: Cargos aos quais a questão se aplica (opcional se disciplina for aplicável a todos)
- `alternativas`: Tabela de alternativas com indicação da correta

**Funcionalidades:**
- Validação dinâmica: campo `designations` é opcional quando a disciplina é aplicável a todos os cargos

---

### 3. Prova

Conjunto de questões vinculado a um Edital.

**Campos principais:**
- `titulo`: Nome da prova
- `edital`: Link para o Edital (obrigatório)
- `designation`: Cargo (preenchido automaticamente do Edital)
- `data_aplicacao`: Data de aplicação
- `duracao_minutos`: Tempo de duração
- `questoes`: Tabela de questões selecionadas
- `status`: Rascunho, Publicada, Aplicada, Encerrada

**Funcionalidades:**
- **Seleção de Questões via Dialog**: Popup com preview do conteúdo para facilitar a seleção
- **Gerador Automático de Provas**: Define disciplinas, quantidade e dificuldade para seleção automática

---

### 4. Edital

DocType central para gestão de processos seletivos.

**Campos principais:**
- `titulo`: Nome do edital
- `numero_edital`: Numeração oficial
- `job_opening`: Vaga vinculada (Link para Job Opening)
- `designation`: Cargo (preenchido automaticamente da vaga)
- `data_publicacao`: Data de publicação
- `data_inicio_inscricoes` / `data_fim_inscricoes`: Período de inscrições
- `etapas`: Tabela de etapas do processo (Interview Rounds)
- `candidatos`: Tabela de candidatos inscritos

**Funcionalidades:**

#### Importação de Candidatos
- Importa candidatos da vaga selecionada
- Funciona mesmo em formulários novos (não salvos)
- Filtra automaticamente candidatos pela vaga

#### Gestão de Etapas
- Etapas vinculadas a Interview Rounds
- Ordem automática baseada na posição na tabela
- Campos de data/hora prevista para cada etapa

#### Avançar Candidatos
- Seleção em lote de candidatos
- Move para próxima etapa com um clique
- Cria automaticamente registros de Interview

#### Criar Entrevistas
- Gera Interviews para todos os candidatos de uma etapa
- Preenche data e horário automaticamente

#### Enviar E-mails
- Notificação em lote para candidatos selecionados

#### Publicar no Blog
- Gera publicação automática no blog do ERPNext
- Inclui informações do edital formatadas

---

### 5. Edital Etapa Item (Child Table)

Etapas do processo seletivo.

**Campos:**
- `interview_round`: Link para Interview Round
- `data_prevista`: Data prevista
- `hora_inicio` / `hora_fim`: Horário da etapa
- `local`: Local de realização
- `observacoes`: Notas adicionais
- `ordem`: Preenchido automaticamente (idx)

---

### 6. Edital Candidato Item (Child Table)

Candidatos inscritos no edital.

**Campos:**
- `job_applicant`: Link para Job Applicant
- `applicant_name`: Nome do candidato
- `email_id`: E-mail
- `etapa_atual`: Etapa atual no processo
- `status_candidato`: Status (Inscrito, Em Avaliação, Aprovado, Reprovado, Desistente)

---

## Print Formats

### 1. Prova Completa
Formato de impressão da prova com todas as questões e alternativas.

### 2. Gabarito
Gabarito da prova com respostas corretas.

### 3. Minuta do Edital
Documento oficial do edital seguindo o regulamento de contratação de pessoal, incluindo:
- Disposições gerais
- Competências
- Requisitos
- Etapas do processo
- Cronograma
- Informações da vaga

---

## Relatórios

### 1. Candidatos por Etapa
Visualização de candidatos agrupados por etapa do processo seletivo.

**Filtros:** Edital

### 2. Candidatos por Status
Distribuição de candidatos por status (Inscrito, Aprovado, Reprovado, etc.).

**Filtros:** Edital  
**Gráfico:** Pizza com distribuição por status

### 3. Comparativo entre Editais
Comparação de métricas entre diferentes editais.

**Métricas:** Total de candidatos, aprovados, reprovados, taxa de aprovação  
**Gráfico:** Barras comparativas

---

## Custom Fields

O módulo cria automaticamente os seguintes Custom Fields nos DocTypes padrão:

### Interview
- `edital`: Link para Edital

### Job Applicant
- `edital`: Link para Edital

**Criação automática:** Os campos são criados via hook `after_migrate`, garantindo que existam após cada migração.

---

## Hooks

```python
# hooks.py
after_install = "integracoes_customizadas.provas.setup.after_install"
after_migrate = "integracoes_customizadas.provas.setup.after_migrate"
```

---

## API / Métodos Whitelisted

### setup.py

```python
@frappe.whitelist()
def criar_custom_fields_edital()
```
Cria manualmente os Custom Fields necessários para o módulo.

**Uso via console:**
```python
from integracoes_customizadas.provas.setup import criar_custom_fields_edital
criar_custom_fields_edital()
```

### edital.py

```python
@frappe.whitelist()
def importar_candidatos(edital_name)
```
Importa candidatos da vaga vinculada ao edital.

```python
@frappe.whitelist()
def avancar_candidatos(edital_name, candidatos, nova_etapa)
```
Move candidatos selecionados para uma nova etapa.

```python
@frappe.whitelist()
def criar_interviews_etapa(edital_name, etapa)
```
Cria registros de Interview para candidatos de uma etapa.

```python
@frappe.whitelist()
def enviar_emails_candidatos(edital_name, candidatos, assunto, mensagem)
```
Envia e-mails para candidatos selecionados.

```python
@frappe.whitelist()
def gerar_publicacao_blog(edital_name)
```
Gera publicação no blog com informações do edital.

### prova.py

```python
@frappe.whitelist()
def gerar_questoes_automaticas(prova_name, config)
```
Gera questões automaticamente baseado em configuração de disciplinas.

---

## Estrutura de Diretórios

```
provas/
├── __init__.py
├── setup.py                    # Instalação e Custom Fields
├── doctype/
│   ├── alternativa_questao/
│   ├── disciplina/
│   ├── disciplina_designation_item/
│   ├── edital/
│   ├── edital_candidato_item/
│   ├── edital_etapa_item/
│   ├── prova/
│   ├── prova_questao_item/
│   ├── questao/
│   └── questao_designation_item/
├── print_format/
│   ├── gabarito/
│   ├── minuta_edital/
│   └── prova_completa/
└── report/
    ├── candidatos_por_etapa/
    ├── candidatos_por_status/
    └── comparativo_entre_editais/
```

---

## Fluxo de Uso Típico

1. **Configuração Inicial**
   - Criar Disciplinas
   - Cadastrar Questões no banco

2. **Abertura de Processo Seletivo**
   - Criar Job Opening (vaga)
   - Criar Edital vinculado à vaga
   - Definir etapas do processo (Interview Rounds)

3. **Inscrições**
   - Candidatos se inscrevem (Job Applicants)
   - Importar candidatos para o Edital

4. **Aplicação de Provas**
   - Criar Prova vinculada ao Edital
   - Usar gerador automático ou selecionar questões manualmente
   - Imprimir prova e gabarito

5. **Gestão do Processo**
   - Avançar candidatos aprovados para próximas etapas
   - Criar Interviews automaticamente
   - Enviar comunicados por e-mail

6. **Acompanhamento**
   - Usar relatórios para análise
   - Comparar editais anteriores

---

## Instalação

O módulo é instalado automaticamente com o app `integracoes_customizadas`.

Para garantir que os Custom Fields existam:

```bash
bench --site [site] migrate
```

Ou manualmente via console:

```python
bench --site [site] console
>>> from integracoes_customizadas.provas.setup import criar_custom_fields_edital
>>> criar_custom_fields_edital()
```

---

## Changelog

### v0.1.0 (2026-01-23)
- Implementação inicial completa do módulo
- DocTypes: Disciplina, Questão, Prova, Edital
- Gerador automático de provas
- Gestão de etapas e candidatos
- Importação local de candidatos (sem necessidade de salvar)
- Ordem automática de etapas
- Print Formats: Prova, Gabarito, Minuta do Edital
- Relatórios: Candidatos por Etapa/Status, Notas, Comparativo
- Custom Fields bidirecionais com HRMS
- Hook after_migrate para criação automática de campos
