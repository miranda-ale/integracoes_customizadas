# ADR-003: Padronização de lint e CI

## Status

Aceita (2026-11-21).

## Contexto

Os 10 apps Frappe do grupo estão sendo preparados para unificação e para a migração v15 -> v16/v17. Antes disso,
os apps divergiam em lint e CI (versão do Python, versão e regras do ruff, ignores, excludes do pre-commit, uso do
prettier/eslint). Esta ADR registra a padronização aplicada a este repositório (`integracoes_customizadas`).

## Decisão

1. **Python: mínimo 3.11 mantido** (`target-version = "py311"`, `requires-python = ">=3.11"`, `linter.yml` em 3.12, ver decisão 18),
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

15. **CI: `bench migrate` antes dos testes.** O `install-app` não executa os hooks `after_migrate` (workspaces,
    cards de Compras/Bionexo, bloco de indicadores do Jurídico, atalhos), que em produção rodam a cada migrate; sem
    isso a política de acesso e o workspace Jurídico falhavam só no CI. O passo "Run Tests" do `ci.yml` roda
    `bench migrate` antes dos testes. (A versão anterior desta decisão criava stubs de DocTypes no setup de teste;
    eles foram removidos, ver decisão 16.)
16. **DocTypes de cadastro criados pela interface em produção agora são instalados pelo app (issue #8).**
    `Municipios`, `CBO`, `Dependentes`, `Colaboradores Link` (tabela do Canal) e `Canal de Denuncias` não pertencem
    a nenhum app do grupo e são referenciados pelos Custom Fields de `Employee`/`Designation` (fixtures) e pelo
    card Ética do workspace Jurídico. As definições estão em `integracoes_customizadas/cadastros/definicoes/*.json`,
    extraídas do site de produção (sem dados), e `cadastros/instalacao.py` as cria em `after_install` e
    `after_migrate` **somente se o DocType não existir**: nunca altera campos, nomeação ou permissões de um site que
    já os tem. Por isso os JSON ficam fora de `<módulo>/doctype/`, que o `migrate` sincroniza por cima do existente.
    Os DocTypes são `custom=1` e mantêm o módulo de produção (`HR`; `Gestor Online`, cujo Module Def é criado se
    faltar). As permissões são as de produção; papel inexistente no site é ignorado. O Custom Field
    `Item.custom_código_bionexo` e `Request for Quotation.custom_tipo_de_contratacao` seguem o export (insert_after,
    hidden, filtros, Property Setter `in_list_view`), criados com `update=False` e Property Setters só se ausentes.
    Os stubs de `tests/site_setup.py` foram removidos.
17. **Política de acesso restrita aos módulos deste app (issue #11).** `politicas/acesso_doctypes.verificar()` varre
    só os DocTypes dos módulos de `modules.txt` (Integracoes Customizadas, Provas, Juridico); os dos outros apps
    (CLM, SST, Ponto, hrms) são fiscalizados nos repositórios donos. `politicas/atalhos.py` (`after_migrate`)
    acrescenta, sem remover nada, os links ausentes dos DocTypes do app ao primeiro workspace existente
    (Integrations, HR, Recruitment, Jurídico). As traduções de rótulos do ERPNext são do `bhcl_theme`: este app não
    tem `translations/*.csv` e `test_traducoes_compras.py` cobre só os rótulos que ele cria.
18. **Padrão institucional de CI/linter.** Python 3.12 no `ci.yml` e no `linter.yml` (piso 3.11 mantido no
    pyproject; nunca 3.14); actions alinhadas (`checkout@v7`, `setup-python@v7`, `setup-node@v7`, `cache@v6`);
    `pre-commit/action` substituída por três passos (instalar pre-commit, cache de `~/.cache/pre-commit`,
    `pre-commit run --all-files`); job `deps-vulnerable-check-environment` separado e informativo (`continue-on-error`) para
    frappe, erpnext e hrms `version-15` (resolve decisão 10); `required_apps` inclui `frappe`; dependências fracas
    (`clm` para o e-mail institucional, `assinatura_eletronica` para o WhatsApp) ficam documentadas no `hooks.py` e no
    `pyproject.toml` e protegidas por guarda (`get_installed_apps()`/`ImportError`), de propósito fora do
    `required_apps`.
19. **Designation obrigatório só no teste (issue #12).** Os Custom Fields de Designation do fixture são
    obrigatórios em produção; os test records do hrms não os preenchem. O passo "Run Tests" chama
    `tests.site_setup.relaxar_obrigatoriedade_designation` depois do `migrate` (que reaplica `reqd=1`). O fixture
    `custom_field.json` não muda.
20. **Semgrep: varredura completa e achados antigos corrigidos (sem novo `nosemgrep`).** O `linter.yml` roda
    `semgrep scan --error --config ./frappe-semgrep-rules/rules --config r/python.lang.correctness .` (varredura
    completa em PR, push na main e disparo manual; o `semgrep ci` só olharia o diff do PR). Dos 66 achados antigos,
    64 foram corrigidos: type hints amplos nos métodos whitelisted (uniões que aceitam o que o cliente já envia),
    `_()` nas mensagens e rótulos de relatório, `str(exc)` nos `.format`, remoção de `frappe.db.commit()` manuais
    (a tarefa em lote do DataJud e o `on_update` do Edital são confirmados pelo Frappe), `self.set(...)` nos
    auxiliares do validate de Importacao Bionexo e um único ponto de renderização Jinja das notificações
    (`whatsapp/notification.py: renderizar_modelo`, mesma engine e recusa de `.__` do `frappe.render_template`,
    sem tratar o texto como caminho de arquivo). Os 3 `nosemgrep` de Provas permanecem. **Em aberto, aguardando
    decisão:** `guest-whitelisted-method` em `whatsapp/webhook.py` (endpoint desligado, responde 501 sem processar;
    sem risco real hoje) e `override-doctype-class` em `hooks.py` (a subclasse `WhatsAppNotification` sobrescreve
    `validate`, `send_an_email` e `send_notification_by_channel`, o que `doc_events` do v15 não cobre; a alternativa
    `extend_doctype_class` só existe no v16).

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
- Dois achados do semgrep em aberto (decisão 20): webhook guest e `override_doctype_class`.
- Atalhos/leitores dos DocTypes de CLM, SST e Ponto: nos repositórios donos.
