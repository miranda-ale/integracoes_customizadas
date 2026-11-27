# integracoes_customizadas

## Dependências

- `required_apps = ["erpnext", "hrms", "rh_brasil", "busca_cnpj"]`: não são frentes independentes. O Jurídico e a
  importação Bionexo usam `busca_cnpj`; o Jurídico usa `rh_brasil.documentos`.
- Dependências **fracas, não declaradas**: `clm` (`email_layout`, e-mail institucional, só se instalado) e
  `assinatura_eletronica` (`servicos.canais`, formatação de WhatsApp). Com guarda, não importe sem checar
  `frappe.get_installed_apps()`.
- Outros apps chamam este app com guarda (`rh_brasil`: WhatsApp da rescisão e variantes; `pulse_gestor`; `assinatura_eletronica`).
- Os patches deste app são nomeados por assunto (sem numeração) e não acompanham a versão.

## Versão, tags e documentação

- `__version__` em `integracoes_customizadas/__init__.py` deve bater com a tag (hoje ambos em 3.0.0). Confira antes de criar a tag.
- **Branch `feature/*` usa o major da `main` + 1** (regra vigente desde 2026-11-01). Minor e patch correm normalmente
  dentro dele: com a `main` em `vX.Y.Z`, a feature nasce em `v(X+1).0.0` e segue `v(X+1).0.1`, `v(X+1).1.0`...
  enquanto estiver na branch. Se a `main` subir de major, a feature sobe junto. Confira a versão da `main`
  (`git show main:integracoes_customizadas/__init__.py`) e `git tag` antes de tagear, e não reutilize número existente.
- Tags fora do histórico do HEAD (`git tag --no-merged HEAD`) não fazem parte do app; ignore tags `rc/*` no CHANGELOG.
- `README.md` e `CHANGELOG.md` são mantidos à mão, só com o que está commitado; atualize os dois junto com mudanças de comportamento.
- Visão geral das dependências entre apps: `../../CLAUDE.md`.
