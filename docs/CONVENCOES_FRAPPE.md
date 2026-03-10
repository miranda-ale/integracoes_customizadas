# Convenções Frappe — Nomeação e Caminhos (Lições Aprendidas)

Este documento consolida regras de **nomeação** e **caminhos** que evitam erros comuns ao desenvolver no Frappe/ERPNext (DocTypes órfãos, `ModuleNotFoundError` em relatórios, paths quebrados em nuvem). Aplique-as em novas implementações e ao criar DocTypes, Reports e código no app.

---

## 1) Nomeação

### 1.1 Nome da classe Python do DocType

O Frappe deriva o nome da classe do controller a partir do **nome do DocType** assim:

- Remove espaços e hífens: `doctype.replace(" ", "").replace("-", "")`
- **Não** aplica title case nem lower em cada palavra

Exemplo: DocType **"CJ Snapshot de Risco"** → classe esperada: **`CJSnapshotdeRisco`** (o "d" de "de" fica minúsculo).

- **Regra:** O nome da classe no arquivo `.py` do DocType deve coincidir **exatamente** com essa derivação. Caso contrário, o Frappe não encontra o controller, trata o DocType como órfão e pode removê-lo no `migrate` (Orphaned DocTypes / Deleting orphaned DocTypes).

| DocType (nome)        | Classe Python correta   |
|-----------------------|-------------------------|
| CJ Snapshot de Risco  | `class CJSnapshotdeRisco(Document)` |
| CJ Parte              | `class CJParte(Document)`           |

O mesmo nome deve ser usado no `__init__.py` do diretório do DocType ao exportar a classe.

### 1.2 Nomes de Report (Script Report) e paths de módulo

O Frappe monta o path do módulo Python do Report com **`scrub(report_name)`**:

- `scrub(txt)` = substitui espaços e hífens por `_` e aplica `.lower()`
- **Não remove acentos** (ç, ã, ê, í, ó, ú, etc.)

O path resultante é usado em `importlib.import_module(...)`. Nomes de módulo em Python devem ser **ASCII**. Se o nome do Report tiver acentos, o path terá caracteres não-ASCII e ocorrerá **`ModuleNotFoundError`**.

- **Regra:** O **nome** e **report_name** dos Script Reports devem ser **somente ASCII** (sem acentos). O nome da pasta do report já segue o padrão sem acentos (ex.: `exposicao_e_provisao_por_mes`, `custos_do_processo_por_periodo`).

| Nome com acento (evitar)           | Nome correto (ASCII)              |
|------------------------------------|-----------------------------------|
| Exposição e Provisão por mês       | Exposicao e Provisao por mes      |
| Custos do Processo por período | Custos do Processo por periodo |

Na documentação ou na UI, pode-se exibir o texto com acentos em parênteses ou em docs separados; no banco e no código, usar sempre o nome ASCII.

### 1.3 Pastas e arquivos (DocTypes, Reports)

- **Pastas** de DocType e Report: sempre em **minúsculas**, **underscore** no lugar de espaços, **sem acentos** (ex.: `cj_snapshot_de_risco`, `custos_do_processo_por_periodo`).
- O nome do arquivo `.json` e do `.py` deve coincidir com o nome da pasta (padrão do Frappe).

---

## 2) Caminhos (paths)

### 2.1 Uso de `frappe.get_app_path()`

Para que o código funcione em **qualquer ambiente** (local e nuvem), use **caminhos relativos ao app** via:

```python
frappe.get_app_path("nome_do_app", "segmento1", "segmento2", "arquivo.json")
```

- O primeiro argumento é o **nome do app** (ex.: `integracoes_customizadas`).
- Os demais são **segmentos relativos à raiz do app**. A raiz do app em termos de `get_app_path` é o diretório onde está o pacote Python do app (ex.: `.../apps/integracoes_customizadas/integracoes_customizadas/`). **Não** duplique o nome do pacote nos segmentos.

Exemplo **correto** (módulo do app, doctype, JSON):

```python
path = frappe.get_app_path(
    "integracoes_customizadas",
    "nome_do_modulo",
    "doctype",
    module_name,
    f"{module_name}.json",
)
```

Exemplo **incorreto** (segmento duplicado faz o path apontar para pasta inexistente):

```python
# ERRADO — evite
path = frappe.get_app_path(
    "integracoes_customizadas",
    "integracoes_customizadas",  # duplicado
    "nome_do_modulo",
    "doctype",
    module_name,
    f"{module_name}.json",
)
```

### 2.2 O que evitar

- **Caminhos absolutos fixos** no código (ex.: `/home/usuario/...`, `C:\...`). Quebram em outro ambiente ou em nuvem.
- **`os.path.abspath()`** com segmentos fixos que dependam da máquina.
- Em comentários ou instruções de execução (ex.: "rode com `exec(open('...').read())`"), preferir exemplo com `get_app_path` em vez de path absoluto.

---

## 3) Resumo rápido

| Item                    | Regra                                                                 |
|-------------------------|-----------------------------------------------------------------------|
| Classe do DocType       | Nome = `doctype.replace(" ", "").replace("-", "")` (ex.: CJSnapshotdeRisco) |
| Nome de Report          | Somente ASCII (sem acentos) para evitar ModuleNotFoundError          |
| Pastas/arquivos         | Minúsculas, underscore, sem acentos                                  |
| Caminhos no código      | `frappe.get_app_path(app, ...)`; não duplicar o nome do app nos joins |
| Paths absolutos         | Não usar; usar sempre get_app_path para portabilidade                 |

---

## 4) Referências no repositório

- DocType controller: `apps/frappe/frappe/model/base_document.py` (derivação do nome da classe).
- Report module path: `apps/frappe/frappe/core/doctype/report/report.py` (`get_report_module_dotted_path` usa `scrub(report_name)`).
- `scrub`: `apps/frappe/frappe/__init__.py` (`def scrub(txt)`).
