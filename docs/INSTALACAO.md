# Instalação e Upgrade — Integrações Customizadas (PT-BR)

## 1) Instalação (app já existe)

- Garantir que o app `integracoes_customizadas` esteja instalado no site.
- Após alterações em DocTypes/Reports:
  - `bench --site <site> migrate`
  - `bench --site <site> clear-cache`
  - `bench restart`

## 2) Deploy / Upgrade

- `git pull` no repositório do app
- `bench --site <site> migrate`
- `bench --site <site> clear-cache`
- `bench restart`

## 3) Fixtures

As fixtures versionadas cobrem os recursos exportados por este app (Custom Fields em Employee, Designation, etc.).

## 4) Módulo Contencioso / Processos Judiciais

Processos judiciais e contencioso passaram para o app **Jurídico**. Para instalação e configuração desse módulo, use o app `juridico` (ex.: `bench install-app juridico`).
