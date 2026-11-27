# Dependencies

Strong dependencies are declared in `required_apps` (`hooks.py`) and may be imported without a guard. Weak
dependencies are optional: import them only after checking `frappe.get_installed_apps()` (and keep an `ImportError`
fallback), never at module import time.

## Strong dependencies (`required_apps`)

| App | Used for |
| --- | --- |
| `frappe/frappe@version-15` | Framework. |
| `frappe/erpnext@version-15` | Buying/Stock chain (Request for Quotation, Purchase Receipt/Invoice, Workspace `Buying`), Supplier, Company. |
| `frappe/hrms@version-15` | Exams module (Job Applicant, Interview Round, Shift Type) and Employee/Designation custom fields. |
| `still-pulse/rh_brasil@develop` | `rh_brasil.documentos.format_cpf` (Legal module) and the Employee CPF field convention. |
| `still-pulse/busca_cnpj@develop` | CNPJ lookup/validation (`busca_cnpj.api.lookup_cnpj`, `confirm_cnpj_data`, `busca_cnpj.cnpj.*`) used by the Legal module and the Bionexo import; its JS helper `busca_cnpj.taxid` is used in `processo_judicial.js` behind a `window.busca_cnpj?.taxid` guard. |

The English names of `busca_cnpj` are used here; the Portuguese aliases it keeps are deprecated and not used.

## Weak dependencies (not declared)

| App | Where | Behavior without it |
| --- | --- | --- |
| `clm` | `institutional_email.py` (`email_layout.render_email`, `is_branded`); Legal indicators (`Pareceres Juridicos` DocType, read only if the DocType exists and the user can read it). | Plain HTML e-mail; opinions card omitted. |
| `assinatura_eletronica` | `whatsapp/modelos.py` (`servicos.canais.whatsapp_para_html`). | Simple HTML conversion of the WhatsApp text. |

## Consumers of this app (reverse dependencies)

Other apps call this app with guards on their side; their imports break if the names below change, so renames of
these modules must keep a deprecated alias until the consumers migrate:

| Consumer | Uses |
| --- | --- |
| `rh_brasil` | `whatsapp.roteador` (`variar_ativo`, `escolher`), `whatsapp.modelos` (`contexto`, `_renderizar_texto`, `_ENV`), hook `whatsapp_contexto_extra`; Employee/Designation custom fields shipped in `fixtures/custom_field.json` (`custom_cpf`, `custom_matricula`, `custom_rg`, `custom_carga_horária_mensal`, ...). |
| `assinatura_eletronica` | `whatsapp.conector` (`normalizar_numero_br`, `estado_conexao`, `verificar_numero`, `EvolutionIndisponivel`, `NumeroInvalido`, `EnvioRejeitado`), `whatsapp.roteador`; WhatsApp status events (`evolution_webhook_handlers` hook). |
| `pulse_gestor` | `whatsapp.modelos.enviar_modelo`, `whatsapp.conector.normalizar_numero_br`. |
| `clm` | References the `Edital` DocType (Exams module, owned by this app); it must treat it as a weak dependency (guard with `frappe.db.exists("DocType", "Edital")`). |

## Ownership notes

- Employee and Designation Custom Fields in `fixtures/custom_field.json` are owned by this app but used by
  `rh_brasil`; they do not follow `custom_<app>_<meaning>` yet (Phase 2: rename with a patch, coordinated with
  `rh_brasil`, which must declare or guard its own use).
- `rh_brasil` must not rely on this app's fixtures implicitly: it should guard with
  `frappe.get_installed_apps()` and check that the Custom Field exists (`frappe.get_meta("Employee").has_field`).

## Custom Field ownership (Employee and Designation)

`rh_brasil` owns the 35 Employee/Designation Custom Fields that both apps used to ship (it lists them by name in its
`hooks.py` fixtures). This app ships only its own 31 (`custom_cpf`, `custom_tipo_de_deficiencia` and the layout fields it
needs) and its export filter lists them by name; `tests/test_fixture_ownership.py` enforces that no field is shipped by
both. The 35 had identical definitions in both apps, so no value changed. Removing a field from a fixture does not delete
it from a site: nothing is dropped on `migrate`.
