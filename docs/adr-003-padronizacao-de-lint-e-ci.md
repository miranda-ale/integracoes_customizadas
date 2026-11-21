# ADR-003: Padronização de lint e CI

## Status

Aceita (2026-11-21).

## Contexto

Os 10 apps Frappe do grupo estão sendo preparados para unificação e para a migração v15 -> v16/v17. Antes disso,
os apps divergiam em lint e CI (versão do Python, versão e regras do ruff, ignores, excludes do pre-commit, uso do
prettier/eslint). Esta ADR registra a padronização aplicada a este repositório (`integracoes_customizadas`).

## Decisão

1. **Python: mínimo 3.11 mantido** (`target-version = "py311"`, `requires-python = ">=3.11"`, `linter.yml` em 3.11),
   por restrição de produção: as imagens de produção/homologação estão confirmadas em Python 3.12. **Alvo de
   migração ao Frappe v16: `>=3.13`** (`target-version = "py313"`, `requires-python = ">=3.13"`, `linter.yml` e
   `ci.yml` coerentes), a executar na migração. O `ci.yml` passou a rodar Python 3.12 (antes 3.14), para refletir a
   produção: o 3.14 é incompatível com o Frappe v15 (o freezegun quebra na coleta de testes com
   `AttributeError: module 'uuid' has no attribute '_load_system_functions'`).
2. **ruff fixado em v0.16.10** via `ruff-pre-commit`, regras `F,E,W,I,UP,B,RUF` e lista de `ignore` do CLM, sem ignores adicionais de `UP` (ver decisão 13).
3. **pyupgrade coberto pela regra `UP` do ruff**, sem hook separado.
4. **F401 NÃO é ignorado**: imports mortos foram removidos; reexportações/efeito colateral são mantidos com
   `# noqa: F401  # <motivo>`. Strings visíveis ao usuário com caractere unicode ambíguo (ex.: travessão) recebem
   `# noqa: RUF001` em vez de alterar o texto.
5. **prettier 2.7.1 e eslint 8.44.0 mantidos**: a atualização foi adiada para não misturar com a padronização;
   revisar na preparação para v16/v17.
6. **Excludes do pre-commit são sempre caminhos do próprio repositório**, entradas mortas removidas, sem ampliar o
   escopo ignorado.
7. **Globais de ESLint declarados no `.eslintrc` com escopo mínimo**: `busca_cnpj` como `"readonly"` (namespace do
   app dependente `busca_cnpj`, usado em `processo_judicial.js`). Nenhum `overrides` foi necessário (não há
   variáveis injetadas pelo Frappe, como `root_element`).
8. **Arquivos JS com Jinja excluídos por caminho exato**: nenhum. O único JS com sintaxe Jinja
   (`juridico/report/relação_de_processos/relação_de_processos.js`) mantém o Jinja dentro de uma template string
   e passa em prettier e eslint normalmente.
9. **JS formatado pelo prettier em commit exclusivo de estilo**: 6 arquivos `.js`.
10. **pip-audit roda só no CI e audita apenas o `pyproject`**; as dependências `erpnext`/`hrms` ficam comentadas,
    então a cobertura é pequena (ver Pendências).
11. **commitlint mantido** e `pre-commit install` documentado em `AGENTS.md`.
12. **Sem tag e sem mudança de `__version__`** nesta padronização.
13. **Consultas SQL de Provas: f-string da `main` mantida, com `# nosemgrep: frappe-sql-format-injection`.**
    As três consultas (`candidatos_por_etapa`, `candidatos_por_status`, `comparativo_entre_editais`) seguem como na
    `main` (f-string, que o `ruff --fix` do UP032 produziu). Verificado que `conditions` é montado só com fragmentos
    constantes (`" AND e.name = %(edital)s"` etc.) e que todos os valores vão por parâmetros nomeados, sem
    interpolar entrada do usuário; por isso o achado é falso positivo e é suprimido, com comentário de
    justificativa, na linha imediatamente anterior à chamada. Alternativa descartada: voltar ao
    `.format(conditions=...)` e restaurar os ignores `UP030/031/032/037/040`. A premissa de que o `.format` evitaria
    o semgrep era falsa: a regra detecta `.format()` e f-string igualmente, e a reversão só aumentaria o diff contra
    a `main` e enfraqueceria o ruff. Os ignores `UP` extras, portanto, **não** foram restaurados.
14. **`get_open_count` (`juridico/dashboard.py`) com `items: str | list | None = None`**, exigido pela regra
    `missing-argument-type-hint`. Validado contra `frappe.utils.typing_validations` (v15): `None`, string JSON e
    lista passam; `dict` e `int` são rejeitados.

15. **CI: stubs de DocTypes inexistentes no setup de teste.** Os Custom Fields de `Employee` e `Designation` em
    `fixtures/custom_field.json` apontam para os DocTypes `Municipios` (`Employee-custom_naturalidade_cidade`), `CBO`
    (`Designation-custom_cbo`) e `Dependentes` (`Employee-custom_dependentes`), que não existem em nenhum app do
    grupo (provavelmente criados à mão em produção). Sem eles, a criação dos test records do hrms falha com
    `WrongOptionsDoctypeLinkError`. O passo "Run Tests" do `ci.yml` chama
    `integracoes_customizadas.tests.site_setup.criar_doctypes_stub` (idempotente, sem hook, só em teste). **A
    instalação limpa do app depende desses DocTypes, que não estão no app**: tarefa de produto separada (criá-los
    no app ou remover/condicionar os campos).

## Consequências

- Ruff, prettier e eslint rodam de forma idêntica local (pre-commit) e no CI; divergências de estilo deixam de
  aparecer em revisões.
- Imports mortos não passam mais despercebidos; reexportações precisam justificar o `noqa`.
- Formatação em lote gerou diffs só de estilo, isolados em commits próprios (`style:`) para não poluir `git blame`
  de mudanças funcionais.
- Prettier e eslint continuam em versões antigas até a preparação para v16/v17.

## Estado deste repositório

| Item | Estado |
| --- | --- |
| F401 (commit `fix: corrigir erros do ruff check`) | 2 nomes mortos removidos (`now_datetime`, `today`); 1 reexportação mantida com `# noqa: F401  # compat` (`bionexo_export.py`) |
| RUF001 | 2 ocorrências com `# noqa: RUF001` (`juridico/agenda.py`) |
| Excludes do pre-commit alterados | Nenhum (prettier e eslint mantêm os excludes originais) |
| ESLint | `busca_cnpj` declarado `readonly`; nenhum bug real de variável indefinida encontrado |
| prettier | 6 arquivos `.js` reformatados; nenhum arquivo não-JS alterado |
| `pre-commit run --all-files` (sem commitlint) | Todos os hooks passam |

## Pendências

- Atualizar prettier (2.7.1) e eslint (8.44.0) na preparação para v16/v17.
- Migrar o alvo Python para `>=3.13` na migração ao v16 (produção/homologação hoje em Python 3.12).
- Ampliar o pip-audit para cobrir as dependências `erpnext`/`hrms` (hoje comentadas no `pyproject`).
