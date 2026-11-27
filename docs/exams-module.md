# Exams module and recruitment process management

**Version:** 0.1.0  
**App:** integracoes_customizadas  
**Module:** Provas (Exams)

## Overview

The Exams module ("Provas") is an ERPNext/HRMS extension that allows complete management of recruitment processes ("processos seletivos"), including:

- Question bank organized by subjects ("disciplinas")
- Automatic exam generation
- Management of recruitment notices ("editais", the public notice that opens a selection process)
- Candidate tracking by stage
- Management reports
- Integration with the standard HRMS DocTypes (Job Applicant, Job Opening, Interview, Interview Round)

---

## DocTypes

### 1. Disciplina (Subject)

Categorizes questions by knowledge area.

**Main fields:**
- `titulo`: Subject name
- `aplicavel_a_todos`: If checked, questions of this subject can be applied to any position
- `designations`: List of positions the subject applies to (when not applicable to all)

---

### 2. Questão (Question)

Question bank used to compose the exams.

**Main fields:**
- `enunciado`: Question text
- `disciplina`: Link to Disciplina
- `nivel_dificuldade`: Easy, Medium or Hard
- `designations`: Positions the question applies to (optional if the subject applies to all)
- `alternativas`: Table of alternatives with the correct one marked

**Features:**
- Dynamic validation: the `designations` field is optional when the subject applies to all positions

---

### 3. Prova (Exam)

Set of questions linked to an Edital.

**Main fields:**
- `titulo`: Exam name
- `edital`: Link to the Edital (required)
- `designation`: Position (filled automatically from the Edital)
- `data_aplicacao`: Application date
- `duracao_minutos`: Duration
- `questoes`: Table of selected questions
- `status`: Draft, Published, Applied, Closed (stored in pt-BR)

**Features:**
- **Question selection via Dialog**: popup with a content preview to ease selection
- **Automatic exam generator**: define subjects, quantity and difficulty for automatic selection

---

### 4. Edital (Recruitment notice)

Central DocType for recruitment process management.

**Main fields:**
- `titulo`: Notice name
- `numero_edital`: Official numbering
- `job_opening`: Linked opening (Link to Job Opening)
- `designation`: Position (filled automatically from the opening)
- `data_publicacao`: Publication date
- `data_inicio_inscricoes` / `data_fim_inscricoes`: Registration period
- `etapas`: Table of process stages (Interview Rounds)
- `candidatos`: Table of registered candidates

**Features:**

#### Candidate import
- Imports candidates of the selected opening
- Works even on new (unsaved) forms
- Automatically filters candidates by opening

#### Stage management
- Stages linked to Interview Rounds
- Automatic order based on the position in the table
- Planned date/time fields for each stage

#### Advance candidates
- Batch selection of candidates
- Moves to the next stage with one click
- Automatically creates Interview records

#### Create interviews
- Generates Interviews for all candidates of a stage
- Fills in date and time automatically

#### Send e-mails
- Batch notification to selected candidates

#### Publish to the blog
- Generates an automatic post on the ERPNext blog
- Includes the formatted notice information

---

### 5. Edital Etapa Item (Child Table)

Stages of the recruitment process.

**Fields:**
- `interview_round`: Link to Interview Round
- `data_prevista`: Planned date
- `hora_inicio` / `hora_fim`: Stage time
- `local`: Venue
- `observacoes`: Additional notes
- `ordem`: Filled automatically (idx)

---

### 6. Edital Candidato Item (Child Table)

Candidates registered in the notice.

**Fields:**
- `job_applicant`: Link to Job Applicant
- `applicant_name`: Candidate name
- `email_id`: E-mail
- `etapa_atual`: Current stage in the process
- `status_candidato`: Status (Registered, Under evaluation, Approved, Rejected, Withdrawn; stored in pt-BR)

---

## Print Formats

### 1. Prova Completa
Exam print format with all questions and alternatives.

### 2. Gabarito
Answer key of the exam with the correct answers.

### 3. Minuta Edital
Official notice document following the personnel hiring regulation, including:
- General provisions
- Responsibilities
- Requirements
- Process stages
- Schedule
- Opening information

---

## Reports

### 1. Candidatos por Etapa
View of candidates grouped by recruitment stage.

**Filters:** Edital

### 2. Candidatos por Status
Distribution of candidates by status (Registered, Approved, Rejected, etc.).

**Filters:** Edital  
**Chart:** Pie with distribution by status

### 3. Comparativo entre Editais
Comparison of metrics between different notices.

**Metrics:** Total candidates, approved, rejected, approval rate  
**Chart:** Comparative bars

---

## Custom Fields

The module automatically creates the following Custom Fields on the standard DocTypes:

### Interview
- `edital`: Link to Edital

### Job Applicant
- `edital`: Link to Edital

**Automatic creation:** the fields are created through the `after_migrate` hook, ensuring they exist after every migration.

---

## Hooks

```python
# hooks.py
after_install = "integracoes_customizadas.provas.setup.after_install"
after_migrate = "integracoes_customizadas.provas.setup.after_migrate"
```

---

## API / Whitelisted methods

### setup.py

```python
@frappe.whitelist()
def criar_custom_fields_edital()
```
Manually creates the Custom Fields the module needs.

**Console usage:**
```python
from integracoes_customizadas.provas.setup import criar_custom_fields_edital

criar_custom_fields_edital()
```

### edital.py

```python
@frappe.whitelist()
def importar_candidatos(edital_name)
```
Imports candidates of the opening linked to the notice.

```python
@frappe.whitelist()
def avancar_candidatos(edital_name, candidatos, nova_etapa)
```
Moves selected candidates to a new stage.

```python
@frappe.whitelist()
def criar_interviews_etapa(edital_name, etapa)
```
Creates Interview records for the candidates of a stage.

```python
@frappe.whitelist()
def enviar_emails_candidatos(edital_name, candidatos, assunto, mensagem)
```
Sends e-mails to selected candidates.

```python
@frappe.whitelist()
def gerar_publicacao_blog(edital_name)
```
Generates a blog post with the notice information.

### prova.py

```python
@frappe.whitelist()
def gerar_questoes_automaticas(prova_name, config)
```
Generates questions automatically based on a subject configuration.

---

## Directory structure

```
provas/
├── __init__.py
├── setup.py                    # Installation and Custom Fields
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

## Typical usage flow

1. **Initial setup**
   - Create Disciplinas
   - Register Questions in the bank

2. **Opening a recruitment process**
   - Create a Job Opening
   - Create an Edital linked to the opening
   - Define the process stages (Interview Rounds)

3. **Registrations**
   - Candidates register (Job Applicants)
   - Import candidates into the Edital

4. **Exam application**
   - Create a Prova linked to the Edital
   - Use the automatic generator or select questions manually
   - Print the exam and the answer key

5. **Process management**
   - Advance approved candidates to the next stages
   - Create Interviews automatically
   - Send e-mail announcements

6. **Follow-up**
   - Use the reports for analysis
   - Compare previous notices

---

## Installation

The module is installed automatically with the `integracoes_customizadas` app.

To make sure the Custom Fields exist:

```bash
bench --site [site] migrate
```

Or manually through the console:

```python
bench --site [site] console
>>> from integracoes_customizadas.provas.setup import criar_custom_fields_edital
>>> criar_custom_fields_edital()
```

---

## Changelog

### v0.1.0 (2026-01-23)
- Complete initial implementation of the module
- DocTypes: Disciplina, Questão, Prova, Edital
- Automatic exam generator
- Stage and candidate management
- Local candidate import (no need to save)
- Automatic stage order
- Print Formats: Prova, Gabarito, Minuta do Edital
- Reports: Candidatos por Etapa/Status, Notas, Comparativo
- Bidirectional Custom Fields with HRMS
- `after_migrate` hook for automatic field creation
