# Instalação e Upgrade — Submódulo Contencioso (PT-BR)

> Este módulo vive dentro do app `integracoes_customizadas`.

## 1) Instalação (app já existe)
- Garantir que o app `integracoes_customizadas` esteja instalado no site.
- Após adicionar DocTypes/Workflows/Reports:
  - `bench --site <site> migrate`
  - `bench --site <site> clear-cache`
  - `bench restart`

## 2) Deploy / Upgrade
- `git pull` no repositório do app
- `bench --site <site> migrate`
- `bench --site <site> clear-cache`
- `bench restart`

## 3) Fixtures (recomendado)
Incluir fixtures para:
- Roles do módulo
- Workflows
- Workspace (atalhos do módulo)
- Reports e Dashboards
- Module Def (Contencioso)
- Number Cards e Dashboard Charts

> Boas práticas:
- Versionar fixtures no repositório
- Evitar fixtures “genéricas” que afetem outros módulos

## 4) Scheduler
- Jobs devem ser desativados por padrão no stub de integração.
- Job de prazos pode ser ativado conforme a política interna (em produção, com monitoramento).

## 5) Configurações opcionais
- `contencioso_integracao_ativa = true` em `site_config.json` para habilitar o stub (controlado).
