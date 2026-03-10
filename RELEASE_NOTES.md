# Release Notes

## v1.3.0 (2026-02-26)

### Removido

- **Módulo de Contratos**: Remoção completa do módulo de Contrato de Trabalho do app.
  - DocType "Contrato de Trabalho" e controller removidos.
  - Job diário de alertas de vencimento de contrato removido.
  - Fixtures exclusivas de Contrato removidas: DocType, Notification, Report, Print Format, Property Setter.
  - Hooks atualizados (fixtures, scheduler_events, override_doctype_class).
  - Documentação (README, INSTALACAO) atualizada.

O app passa a incluir apenas os módulos **Integracoes Customizadas** e **Provas**, além dos Custom Fields em Employee, Designation e Interview-prova.

**Nota:** Em sites onde o app já estava instalado, o DocType "Contrato de Trabalho" e os dados permanecem no banco até desinstalação do app ou remoção manual.
