# Copyright (c) 2026, BHCL and contributors
# For license information, please see license.txt
"""Etapas do ciclo de compras de materiais (Solicitação -> Cotação -> Pedido -> Recebimento -> Fatura).

Read model recomputed on every request (nothing is persisted), same payload as `clm.clm.services.process_view
.get_process_steps` so the front end can mirror the CLM "Etapas do processo" bar. The chain is discovered through the
link fields of the child tables (`material_request`, `purchase_order`, ...), ignoring permissions; each document is
then checked against the viewer, and the ones that cannot be read are only counted (`restricted`). That is what lets
a unit that receives goods (no access to Purchase Invoice) still see where the process stands.
"""

import frappe
from frappe.utils import cint, date_diff, flt, formatdate, getdate, nowdate

# (key, label, doctypes)
STAGES = (
	("request", "Solicitação de Compras", ("Material Request",)),
	("rfq", "Pedido de Cotação", ("Request for Quotation",)),
	("quotation", "Cotação do Fornecedor", ("Supplier Quotation",)),
	("order", "Ordem de Compra", ("Purchase Order",)),
	("receipt", "Recebimento de Compra", ("Purchase Receipt",)),
	("invoice", "Nota Fiscal de Compra", ("Purchase Invoice",)),
)
# The quotation steps may be skipped (direct purchase); the bar draws them inside one dashed group.
OPTIONAL_STAGES = ("rfq", "quotation")
GROUPS = {"rfq": "cotacao", "quotation": "cotacao"}
GROUP_LABELS = {"cotacao": "Cotação · opcional"}
STEP_DOCTYPES = tuple(dt for _key, _label, dts in STAGES for dt in dts)

# (child doctype, parent doctype, link field on the child row, linked doctype)
EDGES = (
	("Request for Quotation Item", "Request for Quotation", "material_request", "Material Request"),
	("Supplier Quotation Item", "Supplier Quotation", "material_request", "Material Request"),
	("Supplier Quotation Item", "Supplier Quotation", "request_for_quotation", "Request for Quotation"),
	("Purchase Order Item", "Purchase Order", "material_request", "Material Request"),
	("Purchase Order Item", "Purchase Order", "supplier_quotation", "Supplier Quotation"),
	("Purchase Receipt Item", "Purchase Receipt", "material_request", "Material Request"),
	("Purchase Receipt Item", "Purchase Receipt", "purchase_order", "Purchase Order"),
	("Purchase Invoice Item", "Purchase Invoice", "material_request", "Material Request"),
	("Purchase Invoice Item", "Purchase Invoice", "purchase_order", "Purchase Order"),
	("Purchase Invoice Item", "Purchase Invoice", "purchase_receipt", "Purchase Receipt"),
)

DOC_FIELDS = {
	"Material Request": ["status", "per_ordered", "transaction_date", "material_request_type"],
	"Request for Quotation": ["status", "transaction_date"],
	"Supplier Quotation": ["status", "supplier_name", "transaction_date"],
	"Purchase Order": [
		"status",
		"supplier_name",
		"transaction_date",
		"schedule_date",
		"per_received",
		"per_billed",
	],
	"Purchase Receipt": [
		"status",
		"supplier_name",
		"posting_date",
		"is_return",
		"per_billed",
		"grand_total",
		"custom_compras_nf_numero",
		"custom_compras_nf_valor",
	],
	"Purchase Invoice": ["status", "supplier_name", "posting_date", "bill_no"],
}
DATE_FIELDS = ("posting_date", "transaction_date")

MR_DONE_STATUSES = ("Ordered", "Received", "Issued", "Transferred")
ORDER_CLOSED_STATUSES = ("Closed", "Completed", "Cancelled")
MAX_DOCS = 150


@frappe.whitelist()
def get_purchase_steps(doctype, name):
	"""Stage bar of a document of the purchasing chain: {current, stages: [...]} (see `build_stages`)."""
	if doctype not in STEP_DOCTYPES:
		frappe.throw(f"DocType fora do ciclo de compras: {doctype}", frappe.ValidationError)
	frappe.has_permission(doctype, "read", doc=name, throw=True)
	names = collect_chain(doctype, name)
	docs = load_docs(names)
	return {
		"current": stage_of(doctype),
		"truncated": cint(sum(len(v) for v in names.values()) >= MAX_DOCS),
		"stages": build_stages(docs),
	}


def stage_of(doctype):
	return next((key for key, _label, dts in STAGES if doctype in dts), None)


def _edges():
	"""EDGES whose link field exists in this version of the child doctype."""
	return [e for e in EDGES if frappe.get_meta(e[0]).has_field(e[2])]


def _neighbours(doctype, name, edges):
	found = set()
	for child, parent, field, target in edges:
		if doctype == parent:
			values = frappe.get_all(
				child, filters={"parent": name, "parenttype": parent}, pluck=field, distinct=True
			)
			found.update((target, v) for v in values if v)
		if doctype == target:
			parents = frappe.get_all(
				child, filters={field: name, "parenttype": parent}, pluck="parent", distinct=True
			)
			found.update((parent, p) for p in parents if p)
	return found


def collect_chain(doctype, name):
	"""{doctype: {names}} of every document connected to the given one (permissions are ignored here)."""
	edges = _edges()
	seen = {(doctype, name)}
	queue = [(doctype, name)]
	while queue and len(seen) < MAX_DOCS:
		current = queue.pop(0)
		for node in _neighbours(*current, edges):
			if node not in seen and len(seen) < MAX_DOCS:
				seen.add(node)
				queue.append(node)
	names = {}
	for dt, docname in seen:
		names.setdefault(dt, set()).add(docname)
	return names


def load_docs(names):
	"""{doctype: [row]} with `restricted` set on the rows the current user cannot read."""
	docs = {}
	for dt, doc_names in names.items():
		meta = frappe.get_meta(dt)
		fields = ["name", "docstatus"] + [f for f in DOC_FIELDS.get(dt, []) if meta.has_field(f)]
		rows = frappe.get_all(dt, filters={"name": ["in", list(doc_names)]}, fields=fields)
		for row in rows:
			row["doctype"] = dt
			row["restricted"] = 0 if frappe.has_permission(dt, "read", doc=row["name"]) else 1
		docs[dt] = rows
	return docs


def is_cancelled(row):
	return row.get("docstatus") == 2 or row.get("status") == "Cancelled"


def _status_label(row):
	if row.get("docstatus") == 0:
		return "Rascunho"
	return frappe._(row.get("status") or "")


def public_doc(row):
	date = next((row.get(f) for f in DATE_FIELDS if row.get(f)), None)
	parts = [row.get("supplier_name"), formatdate(date) if date else None]
	return {
		"doctype": row["doctype"],
		"name": row["name"],
		"title": " · ".join(p for p in parts if p),
		"status_label": _status_label(row),
	}


def build_stages(docs, today=None):
	"""Stage list from {doctype: [row]}; cancelled documents are ignored. Pure: no database access."""
	by_stage = {}
	for key, _label, doctypes in STAGES:
		rows = [r for dt in doctypes for r in docs.get(dt, []) if not is_cancelled(r)]
		by_stage[key] = sorted(rows, key=lambda r: r["name"])
	stages = []
	for key, label, _doctypes in STAGES:
		rows = by_stage[key]
		status, alerts = evaluate_stage(key, rows, by_stage, today)
		stages.append(
			{
				"key": key,
				"label": label,
				"optional": int(key in OPTIONAL_STAGES),
				"group": GROUPS.get(key),
				"group_label": GROUP_LABELS.get(GROUPS.get(key)),
				"status": status,
				"count": len(rows),
				"restricted": sum(1 for r in rows if r["restricted"]),
				"alerts": alerts,
				"docs": [public_doc(r) for r in rows if not r["restricted"]],
			}
		)
	return stages


def _submitted(row):
	return row.get("docstatus") == 1


def _valor_divergente(row):
	"""NF value informed on the receipt that differs from the received total beyond a small tolerance."""
	nf_valor = flt(row.get("custom_compras_nf_valor"))
	if not nf_valor:
		return False
	total = flt(row.get("grand_total"))
	return abs(nf_valor - total) > max(1.0, total * 0.005)


def evaluate_stage(key, rows, by_stage, today=None):
	"""(status, alerts) of a stage: ok | pending | warn | none. Alerts never name restricted documents."""
	today = getdate(today or nowdate())
	alerts = []
	if key == "request":
		if not rows:
			return "none", alerts
		if any(r.get("status") == "Stopped" for r in rows):
			alerts.append("Solicitação interrompida.")
			return "warn", alerts
		done = all(
			_submitted(r) and (r.get("status") in MR_DONE_STATUSES or flt(r.get("per_ordered")) >= 100)
			for r in rows
		)
		return ("ok" if done else "pending"), alerts

	if key == "rfq":
		if not rows:
			return "none", alerts
		return ("ok" if all(_submitted(r) for r in rows) else "pending"), alerts

	if key == "quotation":
		if not rows:
			# Request sent but no supplier answered yet.
			if any(_submitted(r) for r in by_stage["rfq"]):
				alerts.append("Aguardando propostas dos fornecedores.")
				return "pending", alerts
			return "none", alerts
		return ("ok" if any(_submitted(r) for r in rows) else "pending"), alerts

	orders = by_stage["order"]
	open_orders = [
		o
		for o in orders
		if _submitted(o) and o.get("status") not in ORDER_CLOSED_STATUSES and flt(o.get("per_received")) < 100
	]

	if key == "order":
		if not rows:
			return "none", alerts
		if any(r.get("status") == "On Hold" for r in rows):
			alerts.append("Pedido em espera.")
			return "warn", alerts
		return ("ok" if all(_submitted(r) for r in rows) else "pending"), alerts

	receipts = [r for r in by_stage["receipt"] if not r.get("is_return")]
	billable = [r for r in receipts if _submitted(r) and flt(r.get("per_billed")) < 100]

	if key == "receipt":
		overdue = [o for o in open_orders if o.get("schedule_date") and getdate(o["schedule_date"]) < today]
		if overdue:
			atraso = max(date_diff(today, o["schedule_date"]) for o in overdue)
			alerts.append(f"{len(overdue)} pedido(s) com entrega atrasada (até {atraso} dia(s)).")
		if not rows:
			return ("warn" if overdue else "pending" if open_orders else "none"), alerts
		submitted = [r for r in receipts if _submitted(r)]
		sem_nf = [r for r in submitted if not r.get("custom_compras_nf_numero")]
		if sem_nf:
			alerts.append(f"{len(sem_nf)} recebimento(s) sem Nota Fiscal informada.")
		divergentes = [r for r in submitted if _valor_divergente(r)]
		if divergentes:
			alerts.append(f"{len(divergentes)} recebimento(s) com valor da NF diferente do recebido.")
		parcial = [o for o in open_orders if flt(o.get("per_received")) > 0]
		if parcial:
			alerts.append(f"{len(parcial)} pedido(s) com recebimento parcial.")
		if sem_nf or divergentes or overdue:
			return "warn", alerts
		if any(not _submitted(r) for r in receipts) or open_orders:
			return "pending", alerts
		return "ok", alerts

	# invoice
	if billable:
		com_nf = sum(1 for r in billable if r.get("custom_compras_nf_numero"))
		alerts.append(f"{len(billable)} recebimento(s) aguardando fatura ({com_nf} com NF informada).")
	if not rows:
		return ("pending" if billable else "none"), alerts
	if billable or any(not _submitted(r) for r in rows):
		return "pending", alerts
	return "ok", alerts
