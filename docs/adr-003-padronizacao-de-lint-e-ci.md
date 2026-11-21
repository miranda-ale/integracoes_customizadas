# ADR-003: Padronização de lint e CI

## Status

Aceita (2026-11-21).

## Contexto

Os 10 apps Frappe do grupo estão sendo preparados para unificação e para a migração v15 -> v16/v17. Antes disso,
os apps divergiam em lint e CI (versão do Python, versão e regras do ruff, ignores, excludes do pre-commit, uso do
prettier/eslint). Esta ADR registra a padronização aplicada a este repositório (`integracoes_customizadas`).

## Decisão

1. **Python 3.11** em CI, `target-version = "py311"` e `requires-python = ">=3.11"` (alvo a revisar para o v16).
2. **ruff fixado em v0.16.10** via `ruff-pre-commit`, regras `F,E,W,I,UP,B,RUF` e lista de `ignore` idêntica à do CLM.
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
   (`juridico/report/relacao_de_processos/relacao_de_processos.js`) mantém o Jinja dentro de uma template string
   e passa em prettier e eslint normalmente.
9. **JS formatado pelo prettier em commit exclusivo de estilo**: 6 arquivos `.js`.
10. **pip-audit roda só no CI e audita apenas o `pyproject`**; as dependências `erpnext`/`hrms` ficam comentadas,
    então a cobertura é pequena (ver Pendências).
11. **commitlint mantido** e `pre-commit install` documentado em `AGENTS.md`.
12. **Sem tag e sem mudança de `__version__`** nesta padronização.

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
- Revisar o alvo Python (3.11) para o v16.
- Ampliar o pip-audit para cobrir as dependências `erpnext`/`hrms` (hoje comentadas no `pyproject`).
