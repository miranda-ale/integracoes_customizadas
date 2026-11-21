# ADR-001: Guaranteed minimal read access on DocTypes linked by Link fields

## Context
The Legal module (`Processo Judicial` -- lawsuit -- and its child tables) references, through Link and Dynamic Link
fields, standard DocTypes of other apps installed in the bench (ERPNext, HRMS): `Company` and `Currency` (Link, on
`Processo Judicial`) and, through the `Dynamic Link` on `Processo Judicial Parte` (`tipo_parte`), `Employee`,
`Customer` and `Supplier`, plus "Terceiros" (third parties, i.e. patients), linked to `Contact`. This app's own role
for the module, **Usuário Jurídico** (`integracoes_customizadas/fixtures/role.json`), only has its own permission on
the Legal DocTypes themselves (`processo_judicial.json`: `Usuário Jurídico` and `System Manager`); there is no
`Custom DocPerm` fixture in this app today (`integracoes_customizadas/fixtures/` only has `custom_field.json`,
`custom_html_block.json` and `role.json`). Reading `Employee`, `Customer`, `Supplier` and `Contact` for someone who
only has `Usuário Jurídico` therefore depends entirely on a role of another module (HR, Sales, Buying) already granting
read -- the same pattern that, in `clm`, left the base user stuck in the middle of the flow with an empty Link or a
permission error when opening the referenced record, with no hint that the cause was in another module (see, in the
`clm` repository, `docs/adr-006-leitura-minima-em-doctypes-vinculados.md`, which fixed the same problem for `CLM User`
with additive `Custom DocPerm` fixtures).

The other areas of the app do not create their own role: Purchasing deliberately uses the standard ERPNext roles
(`Stock User`, `Purchase User`/`Manager`, `Accounts User`/`Manager` -- see [purchasing-flow.md](purchasing-flow.md)),
which already have guaranteed read on the DocTypes they use because they are the "owner" roles of those masters;
WhatsApp and Exams do not expose Links outside their own module in relevant volume. The principle of this ADR applies
equally to them if they ever get their own role with a Link outside their module.

## Decision
Whenever a DocType of this app gets a Link or Dynamic Link field to a DocType of another module/app -- ERPNext, HRMS,
`busca_cnpj`, `rh_brasil`, `clm` or `assinatura_eletronica` --, the basic/daily-use role of that flow (today,
**Usuário Jurídico** for the Legal module) must have at least read permission (`read`, which covers use in Link and
Dynamic Link dropdowns -- equivalent to or greater than `select`) on the referenced DocType, regardless of whether any
role of another module grants that read. This is implemented as a `Custom DocPerm` fixture registered in `fixtures/`
and in `hooks.py`, never by editing the other app's DocType.

`Custom DocPerm` is **additive**: it adds a permission row to the other app's DocType and does not replace or remove
the standard permissions that DocType already has for other roles -- it is the same mechanism used by `clm` in the
ADR-006 cited above, with no side effect on anyone who already reads the master through another role. (This confusion
appeared in [purchasing-flow.md](purchasing-flow.md) as a reason not to use `Custom DocPerm`; it was corrected in the
same commit as this ADR.)

When adding a Link/Dynamic Link field to a DocType outside the app on any DocType of this repository, the change is
only complete once the read fixture exists for that DocType (or already existed from a previous change) for the basic
role(s) of the affected flow.

## Finding while writing this ADR (open item, not fixed here)
This task is documentation only -- no permission was changed. Reviewing the current state:

- `Processo Judicial Parte.tipo_parte` links, by Dynamic Link, to `Employee`, `Customer` and `Supplier` (and to
  `Contact`, for "Terceiros"). `Usuário Jurídico` has no read fixture of its own on any of these four DocTypes; read
  access today depends on that role also having (or a user accumulating) an HR, Sales or Buying role -- exactly the
  implicit pattern that `clm`'s ADR-006 identified as the cause of blocking in the middle of the flow. It was not
  possible to confirm in this session, without the `erpnext`/`hrms` source available locally, whether any of these
  DocTypes grants read to `Usuário Jurídico` by another route (e.g. an `All` role with broad read); verifying this
  and, if the gap is confirmed, opening the corresponding `Custom DocPerm` fixture in a dedicated change is left as
  an open item (outside the scope of this task).
- `Supplier`, filled by the Bionexo import through the CNPJ lookup of `busca_cnpj` (`bionexo/import_pdf.py`), is
  read/created by the standard Buying roles (`Purchase User`/`Manager`), which already have their own permission on
  `Supplier` in ERPNext -- there is no gap here, since this app does not introduce its own role for that flow.
- `rh_brasil.documentos` (used in `juridico/doctype/processo_judicial/processo_judicial.py` and `juridico/parte.py`
  through `format_cpf`) is a module of utility functions, not a DocType -- there is no Link field to an `rh_brasil`
  DocType in this app today, so it does not apply to this finding.

## Consequences
- Once the minimal read fixture is actually created for the DocTypes above, no Legal flow should block the base user
  for lack of read on a linked master of another module: the cross dependency stops being implicit and becomes
  explicit and guaranteed by `integracoes_customizadas` itself.
- The intended scope is read only: `write`, `create` and `delete` on those DocTypes remain outside this app's scope
  and keep being governed by the roles that already administer them (HR, Sales, Buying, etc.).
- PR review: every PR that introduces a Link/Dynamic Link field to a DocType external to the app must check whether
  the read fixture already covers that DocType for the basic role of the flow; if not, add it in the same commit (or,
  if it is only noted and not fixed, record the gap as an explicit open item, as done above).
