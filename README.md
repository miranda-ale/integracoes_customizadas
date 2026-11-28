# Custom Integrations (`integracoes_customizadas`)

A set of ERPNext/HRMS integrations and customizations. Current version: **4.1.0** (see
[CHANGELOG.md](CHANGELOG.md)). The app bundles four areas that share some services (for example `busca_cnpj` in the
Bionexo import and the `clm` e-mail layout):

| Area | Module | What it delivers |
| --- | --- | --- |
| **WhatsApp** notifications | Integracoes Customizadas | Evolution API v2, templates with variants, multiple instances |
| **Legal** ("Jurídico") | Juridico | Lawsuit (Processo Judicial) with DataJud, legal management, provisioning, agenda and reports |
| **Exams** ("Provas") | Provas | Question bank, exams and recruitment notices (editais) |
| **Purchasing** ("Compras") | Integracoes Customizadas | Bionexo, Price Map, Nota Fiscal (tax invoice) on receipt, process stages and lean workspaces |

There are also cross-cutting features: [uppercase normalization of records](#record-normalization),
[DocType access check](#doctype-access-policy) and custom fields through fixtures.

## Features

### WhatsApp notifications (Evolution API v2)

**Sending**

- **Also send by WhatsApp** option on `Notification` rules. The rule requires a **WhatsApp Template** ("Modelo
  WhatsApp") and sends the subject and message to the selected users, at the number in the *Mobile* field
  (`mobile_no`) of the user record.
- **Recipients without a user:** *Phone* fields of the document (including child tables), chosen in the *Recipients*
  table, and the **Additional WhatsApp numbers** field (one per line, accepts Jinja). Repeated numbers receive a
  single message.
- **Print format attachment:** with "Attach Print" and a "Print Format" on the rule, the PDF is generated at send time
  (with the same draft and cancelled guards as e-mail) and sent as a document; the text becomes the caption.
  15 MB limit.
- Brazilian numbers with an area code (DDD) automatically get the 55 prefix; international numbers must be informed in
  full, with `+` and the country code.

**Templates and variants**

- **Modelo WhatsApp** DocType with alternative wordings (**Variante Modelo WhatsApp**). The router draws one variant per
  recipient, without repeating the previous one or the last one received by the same number; the Jinja function
  `sorteio("Oi","Olá")` varies snippets inside the message. The switch is **Vary messages** in WhatsApp Settings
  (Configuracoes WhatsApp).
- **At least 10 active variants** for the template to be active. Templates created by code receive seed wordings
  (`seed/template_variants.py`) and the patches `semear_variantes_modelo_whatsapp` and
  `completar_variantes_modelo_whatsapp` complete the existing ones (those without a seed go to the Error Log).
- Extension hooks: `whatsapp_contexto_extra` (extra variables in the template context) and
  `evolution_webhook_handlers`.

**Connection and instances**

- **Configuracoes WhatsApp** (Single): base URL, global key, main instance, active, timeouts, interval between sends and
  prior number verification. Actions to **create the instance** (reports whether it was created or already existed),
  **generate a QR Code** and **refresh the state** of the connection.
- **Routing between instances:** the *Additional instances* table (**Instancia WhatsApp**, with optional weight and
  daily limit) adds to the main one; `whatsapp/dispatcher.py` uses the connected instance with the lowest load of
  the day, with affinity per recipient and failover. Without additional rows the behavior does not change.
- **Stable connector** (`whatsapp/conector.py`): `estado_conexao`, `verificar_numero`, `enviar_texto`,
  `normalizar_numero_br`; no retry on send.
- **Envio WhatsApp:** record per recipient with state, instance, variant, format and file, and a **Resend** button for
  failures.
- The Evolution webhook endpoint is **reserved and turned off** (answers HTTP 501).
- E-mails of Notifications (E-mail channel), of the WhatsApp Template (E-mail channel or fallback) and of the Edital
  stage advance use the institutional layout of `clm` (`institutional_email.py`, weak dependency).
- Settings and send records are restricted to system administrators.

### Legal (`Juridico` module)

**Registration and DataJud**

- **Processo Judicial** in draft or completed, with CNJ number, court, company, phase, risk, status, subjects and
  movements. Data coming from DataJud is protected against manual editing.
- **Parties:** table of parties with a main party, including parties without a registration and identification of
  former employees; the *Terceiros* (third parties, i.e. patients) option links to Contacts.
- **DataJud Settings:** lookup by CNJ number and court, manual fetching of case updates and automatic follow-up of
  lawsuits in progress (business days at 03:00, in a single batch on a dedicated `datajud` queue, never one lawsuit
  per task again). 100 s timeout on interactive queries (12 s in batch); on failure, the previous data is preserved,
  the error is classified and grouped in **DataJud Sync Log**, and a circuit breaker pauses the automatic
  synchronization after consecutive failures (see [docs/datajud-log-quality.md](docs/datajud-log-quality.md)).
  Attachment per movement, with reading of sub-movements.
- **Links** with Employee, Customer, Supplier, Contact and related lawsuits, in the connection panels.

**Legal management (v3.0.0)**

- **Internal classification:** nature (Labor, Civil, Tax, Other), action type, subject matter, internal folder/code
  (unique per company) and internal responsible person.
- **Lawyers:** name, validated OAB (`123456/SP`), law firm, internal/external type and fees.
- **Claims and provisioning:** loss probability (Probable/Possible/Remote) and probable amount per claim; the
  suggested provision adds up the probable claims and can be overridden (`provisao_manual`). The lawsuit probability is
  that of the worst claim; `risco` stays manual.
- **Hearings and deadlines:** each row keeps a ToDo (and an Event, for hearings) without duplicating; it closes when
  the result is entered and cancels when removed. A daily job at 07:00 alerts about deadlines overdue or due within
  3 days.
- **Financial:** judicial/appeal deposits, settlements and costs with computed totals; result (upheld, dismissed,
  settlement) and closing date.

**Indicators and reports**

- **Dashboard View** *Integ Legal Cases*: cards (total, in progress, closed) and charts by status, risk, phase, court,
  IBGE locality and most frequent subjects; **Juridico Indicadores** panel in the workspace (see
  [docs/legal-dashboard.md](docs/legal-dashboard.md)).
- Reports: **Integ Legal Cases List** (filters by company, party, phase, status, subject, court, instance, risk, nature,
  responsible person, number and period; own print/PDF), **Integ Legal Cases Provision**, **Integ Legal Cases Liability**,
  **Integ Legal Cases by Employee** and **Integ Legal Cases Aging**.
- **Juridico** workspace (label "Jurídico", with a shortcut to the `clm` Legal Opinions) and **Integ Legal User**
  role. The legacy *Contencioso* (litigation) was removed by patches.

### Exams (`Provas` module)

- **Disciplina** and **Questão**: question bank by knowledge area, difficulty and position (`Designation`), with
  alternatives and the correct one marked.
- **Prova** (submittable): composition from the question bank, linked to an Edital.
- **Edital**: recruitment processes with stages and candidates, integrated with HRMS *Job Applicant*, *Job Opening*
  and *Interview*.
- **Reports:** Integ Candidates by Stage, Integ Candidates by Status and Integ Notice Comparison.
- **Print formats:** Integ Notice Draft, Integ Full Exam and Integ Exam Answer Key.
- Details in [docs/exams-module.md](docs/exams-module.md) (the document header still says "Version 0.1.0").

### Purchasing (Compras)

**Bionexo**

- **Export:** *Export Bionexo XML* button on the submitted `Request for Quotation`, in the Bionexo XML layout.
- **PDF import** (`Importacao Bionexo`, *Bionexo* card in the Purchasing workspace or *Import Bionexo PDF* button on the
  submitted quotation): reads the "general PDC report" and identifies the Request for Quotation (by the name stored in
  Remarks by the exported XML or by the Bionexo ID), the items (`item_code` or `custom_código_bionexo`) and the suppliers
  (full CNPJ; without a valid CNPJ in the record, by name).
  - The identified RFQ must have items of the report and cannot belong to another Bionexo quotation (a copied quotation keeps the
    title of the previous one). With the Purchase Request or the Request for Quotation already chosen, the PDF does not replace them.
  - Unregistered suppliers are created with the CNPJ lookup of `busca_cnpj` (without it, with the name and CNPJ from the
    report); unidentified items are matched by hand or ignored.
  - On submit, generates one submitted `Supplier Quotation` per supplier and one draft `Purchase Order` per supplier with
    the "Confirmed" items (Bionexo quantity and price; PO date = Bionexo confirmation).
  - Completion window: quotations only for the confirmed items and the winners; the *Also generate quotations for the
    other suppliers* box (checked) includes the others with all quoted items.
  - A Purchase Request without a Request for Quotation generates the Request for Quotation from the report. The company
    follows the chosen Request (*References* section).
  - Cancelling deletes the draft POs, cancels the quotations and the generated Request for Quotation; sent POs are cancelled first.
    A submitted import does not block cancelling or deleting the PO, the quotation, the Request for Quotation and the Purchase
    Request (deleting one clears the reference in the import and records a comment on it).
- **Price Map RFQ** ("Integ RFQ Price Map"): comparative report of the `Request for Quotation` (item per row, supplier per
  column), through the *Price Map* button of the quotation.

**Receipt and flow**

- **Supplier Nota Fiscal** on the Purchase Receipt (number, series, validated access key, date, amount, attachment;
  editable after submit); the Purchase Invoice inherits `bill_no` and `bill_date`.
- Reports **Integ Orders to Receive** (*Receive* button) and **Integ Received Not Invoiced** (*Create Invoice* button).
- **Process stages** bar (Request → Quotation → Order → Receipt → Invoice) on the chain forms; documents without read
  permission are only counted.
- **Lean Purchasing and Stock workspaces**, defined in `procurement/workspaces.py` and reapplied on every migrate.
- Tax sections collapsed by default and chain labels translated to pt-BR.
- See [docs/purchasing-flow.md](docs/purchasing-flow.md).

### Record normalization

Names of Employee, Company, Supplier, Customer, Item, Contact, Address, Lead, Department and Designation are kept in
uppercase and without accents (`doc_events["*"]` hook in `normalization/uppercase.py` and `uppercase.js`). The patch
`maiusculas_nomes_existentes` applies the rule to old records.

### DocType access policy

On every `migrate`, `policies/doctype_access.py` warns about orphan or unreachable DocTypes of the app (covered by
`test_politica_acesso`).

### Custom fields (fixtures)

- `Employee` fields (personal documents, labor data, dependents, PCD (persons with disabilities), ethnicity) and
  `Designation` fields (CBO occupation code, education, professional council, activity description).
- `Integ Legal User` role and the `Relatórios` Custom HTML Block. The *Juridico Indicadores* panel is applied by code
  (`juridico.setup`), not by fixture.

## Requirements

- Frappe v15 and the apps `erpnext`, `hrms`, `rh_brasil` and `busca_cnpj` (`required_apps`); see
  [docs/dependencies.md](docs/dependencies.md)
- `clm` (optional): institutional e-mail layout and Opinions/Supplier Documents shortcuts
- For WhatsApp: an [Evolution API](https://doc.evolution-api.com) v2 instance
- For Legal: access to the public DataJud API (CNJ)
- For the Bionexo import: `pypdf` (already present in the Frappe environment; not declared in `pyproject.toml`)

## Installation

```bash
cd $PATH_TO_YOUR_BENCH
# 1. system packages declared by the apps (OCR, WeasyPrint Pango); needs sudo
bash apps/integracoes_customizadas/scripts/install_system_deps.sh   # --dry-run only lists (without the app yet: sudo apt install ocrmypdf tesseract-ocr-por ghostscript qpdf pngquant libpango-1.0-0 libpangoft2-1.0-0)

# 2. apps, in dependency order (ERPNext and HRMS always on version-15)
bench get-app erpnext --branch version-15
bench get-app hrms --branch version-15
bench get-app still-pulse/clm --branch main
bench get-app still-pulse/rh_brasil --branch main
bench get-app still-pulse/busca_cnpj --branch main
bench get-app miranda-ale/integracoes_customizadas --branch main
# optional apps of the suite: still-pulse/assinatura_eletronica, still-pulse/pulse_gestor, still-pulse/pdf_ocr,
# still-pulse/theme_bhcl_erp_next (bhcl_theme), still-pulse/bhcl_site (all --branch main)

# 3. install on the site, in this order
bench --site <site> install-app erpnext hrms busca_cnpj clm rh_brasil integracoes_customizadas
bench --site <site> migrate
```

`required_apps` pins `frappe/hrms@version-15` and `frappe/erpnext@version-15`; without `@branch` bench would use the
default branch (`develop`, v17). `--resolve-deps` only reads the `hooks.py` of repositories reachable without
authentication; for private ones, clone in the order above.

`migrate` runs the `after_migrate` hooks (Exams, Legal, Notification field, Bionexo card, Purchasing and access
check) and the pending patches.

## WhatsApp configuration and usage

1. Open **Configuracoes WhatsApp** in the Desk, enter base URL, global key and instance name, and save.
2. Click **Create instance**, then **Generate new QR Code**; scan it in WhatsApp's *Linked devices* and use **Refresh
   state** to confirm the connection. The same button renews the session. For more than one number, fill in
   *Additional instances* and repeat the process per instance.
3. Create or review the **Modelo WhatsApp** (at least 10 active variants).
4. On the desired **Notification** rules, check **Also send by WhatsApp** and choose the Template.
5. Check **Envio WhatsApp** to see the result per recipient and resend the records with state **Failed**.

## Development

```text
integracoes_customizadas/
├── whatsapp/        # api, conector, distribuidor, roteador, modelos, delivery, notification, setup, webhook
├── juridico/        # datajud, party, agenda_alerts, indicators, report_helpers, dashboard, setup, DocTypes, reports, workspace
├── provas/          # DocTypes, reports, print formats
├── bionexo/         # export_xml · import_pdf (PDF reading) · importacao · setup
├── procurement/         # receipt (NF) · process_view (stages) · workspaces · setup
├── normalization/   # uppercase.py
├── policies/        # doctype_access.py
├── seed/            # template_variants.py (seed wordings)
├── institutional_email.py
├── integracoes_customizadas/   # WhatsApp and Importacao Bionexo DocTypes, reports Integ RFQ Price Map, Integ Orders to Receive, Integ Received Not Invoiced
├── patches/ · fixtures/ · public/ (css and js) · docs/
└── tests/           # 14 files (WhatsApp, Bionexo, Purchasing, Legal, uppercase, access policy)
```

There is also `juridico/doctype/processo_judicial/test_processo_judicial.py`.

Tests (from the bench root):

```bash
bench --site <site> run-tests --app integracoes_customizadas
```

The app uses `pre-commit` (ruff, eslint, prettier, pyupgrade):

```bash
cd apps/integracoes_customizadas
pre-commit install
```

## Documentation

- [CHANGELOG.md](CHANGELOG.md): history by version
- [docs/dependencies.md](docs/dependencies.md)
- [docs/purchasing-flow.md](docs/purchasing-flow.md)
- [docs/legal-dashboard.md](docs/legal-dashboard.md)
- [docs/exams-module.md](docs/exams-module.md)
- [docs/adr-001-minimal-read-on-linked-doctypes.md](docs/adr-001-minimal-read-on-linked-doctypes.md)
- [docs/adr-002-log-quality-and-readability.md](docs/adr-002-log-quality-and-readability.md)
- [docs/adr-003-lint-and-ci-standardization.md](docs/adr-003-lint-and-ci-standardization.md)
- [docs/adr-004-language-and-naming-standardization.md](docs/adr-004-language-and-naming-standardization.md)
- [docs/datajud-log-quality.md](docs/datajud-log-quality.md)

## License

Proprietary (StillPulse Tecnologia LTDA). See `license.txt`.
