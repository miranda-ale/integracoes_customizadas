# integracoes_customizadas

O restante das instruções do repositório está em `CLAUDE.md`. Regra de versão:

- **Branch `feature/*` usa o major da `main` + 1** (regra vigente desde 2026-11-01). Minor e patch correm normalmente
  dentro dele: com a `main` em `vX.Y.Z`, a feature nasce em `v(X+1).0.0` e segue `v(X+1).0.1`, `v(X+1).1.0`...
  enquanto estiver na branch. Se a `main` subir de major, a feature sobe junto. Confira a versão da `main`
  (`git show main:integracoes_customizadas/__init__.py`) e `git tag` antes de tagear, e não reutilize número existente.
