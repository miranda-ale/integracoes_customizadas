# Materials purchasing flow: receipt, Nota Fiscal (tax invoice) and stages

## ERPNext cycle

`Material Request → (Request for Quotation → Supplier Quotation) → Purchase Order → Purchase Receipt → Purchase Invoice`

Quotation (RFQ and Supplier Quotation) is optional. The links live in the item rows (`material_request`,
`supplier_quotation`, `purchase_order`, `purchase_receipt`); the Purchase Order tracks `per_received` and
`per_billed`. Services purchasing follows the dedicated `clm` chain and does not go through here.

## Client flow

1. **Purchasing** closes the Purchase Order.
2. The **unit** opens the **Pedidos a Receber** (orders to receive) report (shortcut in the Purchasing and Stock
   workspaces). Only orders that are submitted, not fully received, with at least one stock item and within the
   user's *User Permissions* (Company/Warehouse) appear. *Receive* opens a pre-filled Purchase Receipt.
3. On receipt the unit checks the quantities and fills the **Supplier Nota Fiscal** section: number, series, access
   key, date, amount and attachment. The key is validated (44 positions and check digit, including the alphanumeric
   CNPJ) and fills number and series. The fields can be filled after submitting.
4. **Purchasing/Finance** opens **Recebidos a Faturar** (received, to be invoiced): submitted receipts not yet invoiced,
   with the NF informed, the difference to the received amount and the *Create Invoice* button. The Purchase
   Invoice inherits `bill_no` and `bill_date` from the receipt (if there is a single source receipt).

Warnings (never blocking): number different from the key, issuer CNPJ different from the supplier (only when
`tax_id` has 14 characters), NF amount different from the received one (tolerance: the greater of R$ 1.00 and 0.5%).

## Permissions

There is no new role. `Stock User` already creates and submits Purchase Receipt and reads Purchase Order; it does
**not** access Purchase Invoice. No *Custom DocPerm* was created here because the standard Purchasing/Stock roles are
already the "owners" of the chain DocTypes; the reason is not that `Custom DocPerm` replaces standard permissions --
it is **additive** (it adds a permission row, it does not replace or remove the existing ones of other roles), as the
`clm` precedent shows (ADR-006, `docs/adr-006-leitura-minima-em-doctypes-vinculados.md` in that repository) and as
this app now also documents in [docs/adr-001-minimal-read-on-linked-doctypes.md](adr-001-minimal-read-on-linked-doctypes.md).
Each unit is restricted to its Company/Warehouse by *User Permission*. Reports: *Pedidos a Receber* for Stock
User/Manager and Purchase User/Manager; *Recebidos a Faturar* for Purchase and Accounts User/Manager.

## Process stages

Collapsible bar at the top of Material Request (Purchase type), RFQ, Supplier Quotation, Purchase Order, Purchase
Receipt and Purchase Invoice, in the same pattern as `clm` (`clm_process_steps`). Six nodes: Purchase Request,
**Request for Quotation** and **Supplier Quotation** (both inside a dashed outline "Quotation · optional", since the
purchase can go straight from the Request to the Order), Purchase Order, Purchase Receipt and Purchase Invoice (same
names used in the rest of the system).

- `procurement/process_view.py`: `get_purchase_steps(doctype, name)` discovers the chain through the item links (up to
  150 documents), ignoring permissions, and marks as `restricted` what the user cannot read (it only enters the
  count). That is why the unit sees the invoice as an existing stage without having access to it.
- Status: `ok`, `pending`, `warn`, `none`. Alerts: late delivery (`schedule_date`), partial receipt, received without
  NF, NF amount mismatch, receipt awaiting invoice. Cancelled documents are ignored.
- The stage list exists in Python (`STAGES`) and in JS (`procurement.steps.STEPS`): keep both equal.
- Front end: `public/js/procurement_steps.js` and `public/css/procurement_steps.css` (loaded by `app_include_*`; bump the
  `?v=` in `hooks.py` on every change).

## Purchase Receipt form

`procurement/setup.py` (`after_migrate`, idempotent) creates the `custom_compras_nf_*` Custom Fields and leaves the tax
sections of the Receipt (*Taxes and Charges* and *Tax Breakup*), of the Order and of the Purchase Invoice (*Taxes and
Charges*) collapsed by default, like *Additional Discount*. English labels of the whole chain (MR, RFQ, SQ, PO, PR,
PI and items) were translated in `bhcl_theme/translations/pt*.csv`; the client looks up the exact key (including a
trailing space, as in `"Accounting Dimensions "`), and `tests/test_procurement_translations.py` warns when a new label
appears without translation.

## Purchasing and Stock workspaces

The layout of both workspaces is defined in `procurement/workspaces.py` (`LAYOUTS`) and reapplied on every `migrate`;
adjustments made through the UI in these two workspaces are overwritten. To change it, edit `LAYOUTS`. The function
only saves when something changed, and nonexistent targets (e.g. a report removed from ERPNext) are ignored.

- **Purchasing** (purchasing team): shortcuts in flow order (Request → Request for Quotation → Quotation → Order →
  Pedidos a Receber → Receipt → Recebidos a Faturar → Invoice), with counters without a company filter (they respect
  User Permissions), and the cards Purchasing flow, Bionexo, Masters (Supplier, Item, Price List), Reports and
  Settings.
- **Stock** (warehouse): shortcuts Pedidos a Receber, Receipt, Stock Entry, Stock Balance, Request and Item; cards
  Receiving and stock flow, Queries, Masters (Item only) and Settings. No number cards or chart.
- Each workspace opens with a numbered card of its flow (in a usage test, people did not notice the shortcuts, only
  the cards). In Purchasing, **Purchasing flow**: 1. Purchase Request ... 8. Purchase Invoice. In Stock,
  **Receiving and stock flow**: 1. Pedidos a Receber, 2. Purchase Receipt, 3. Stock Entry, 4. Stock Balance,
  5. Purchase Request (replenishment). Each user sees only the links they can read.
- Removed: functions unused on the site (0 records in Oct/2026: Delivery Note, Pick List, Serial No, Scorecard,
  Product Bundle, Pricing Rule, Quality Inspection, Landed Cost, etc.), the Learn/Dashboard shortcuts and the old
  English copy of the links. Copy of the previous state: `Workspace` dump before the change (not versioned).
- A card only appears with the links the user can read; Settings disappears for those who only have Stock User.
- Units with the Purchasing or Stock module blocked by the Module Profile still do not see these workspaces.

## Tests

`bench --site dev run-tests --app integracoes_customizadas --module integracoes_customizadas.tests.test_procurement_process`
(and `test_procurement_workspaces`, `test_procurement_translations`)
