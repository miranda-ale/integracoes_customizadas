# Copyright (c) 2026, BHCL and contributors
# For license information, please see license.txt
#
# Comparative price map for a Request for Quotation: one item per row, one supplier per column.
# Adapted from the CLM "CLM Mapa de Precos" report (which reads CLM Quotation Request).

import frappe
from frappe.utils import cint, flt

DISCARDED_STATUSES = ("Stopped", "Cancelled")


def col(label, fieldname, fieldtype="Data", options=None, width=120):
	column = {"label": frappe._(label), "fieldname": fieldname, "fieldtype": fieldtype, "width": width}
	if options:
		column["options"] = options
	return column


def summary(label, value, datatype="Int", indicator=None):
	entry = {"label": frappe._(label), "value": value, "datatype": datatype}
	if indicator:
		entry["indicator"] = indicator
	return entry


def list_records(doctype, filters=None, fields=None, order_by=None, **kwargs):
	"""`frappe.get_list` (respects permissions) without the default 20-row limit."""
	return frappe.get_list(
		doctype,
		filters=filters or [],
		fields=fields or ["name"],
		order_by=order_by,
		limit_page_length=0,
		**kwargs,
	)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.request_for_quotation:
		frappe.throw(frappe._("Selecione a Solicitação de Cotação."))

	include_description = cint(filters.include_description)
	empty = lambda message: (_base_columns(include_description), [], frappe._(message), None, None)  # noqa: E731

	items = list_records(
		"Supplier Quotation Item",
		[["request_for_quotation", "=", filters.request_for_quotation]],
		fields=["parent", "item_code", "item_name", "description", "qty", "rate", "amount", "idx"],
		order_by="idx asc",
		parent_doctype="Supplier Quotation",
	)
	if not items:
		return empty("Nenhuma cotação para esta solicitação.")

	quotation_names = list({item.parent for item in items})
	quotations = list_records(
		"Supplier Quotation",
		[["name", "in", quotation_names]],
		fields=["name", "supplier", "supplier_name", "status", "docstatus", "grand_total"],
	)

	def discarded(quotation):
		return quotation.docstatus == 2 or quotation.status in DISCARDED_STATUSES

	if not cint(filters.include_discarded):
		quotations = [quotation for quotation in quotations if not discarded(quotation)]
	if not quotations:
		return empty("Nenhuma cotação válida para esta solicitação.")

	quotations.sort(key=lambda quotation: flt(quotation.grand_total))
	valid_names = {quotation.name for quotation in quotations}
	items = [item for item in items if item.parent in valid_names]

	supplier_names = list({quotation.supplier for quotation in quotations})
	tax_ids = {
		supplier.name: supplier.tax_id
		for supplier in list_records("Supplier", [["name", "in", supplier_names]], fields=["name", "tax_id"])
	}

	show_global = cint(filters.include_global_value)

	columns = _base_columns(include_description)
	fields_of = {}
	for index, quotation in enumerate(quotations):
		number = index + 1
		suffix = f" ({quotation.status})" if discarded(quotation) else ""
		supplier_label = f"{quotation.supplier_name or quotation.supplier}{suffix}"

		def metric_column(metric, metric_label, fieldname, width):
			label = f"{supplier_label} — {metric_label}" if show_global else supplier_label
			column = col(label, fieldname, "Currency", None, width)
			# supplier_number/supplier_tax_id/metric/metric_label são usados só no formato de impressão,
			# para agrupar as colunas do mesmo fornecedor sob um número (ao invés do nome completo)
			column["supplier_number"] = number
			column["supplier_tax_id"] = tax_ids.get(quotation.supplier)
			column["metric"] = metric
			column["metric_label"] = metric_label
			column["discarded"] = 1 if discarded(quotation) else 0
			return column

		rate_field = f"p_{index}"
		columns.append(metric_column("rate", "Preço Unitário", rate_field, 140))
		quotation_fields = {"rate": rate_field, "global": None}

		if show_global:
			global_field = f"{rate_field}_global"
			columns.append(metric_column("global", "Valor Global", global_field, 120))
			quotation_fields["global"] = global_field

		fields_of[quotation.name] = quotation_fields

	columns.append(col("Média", "average", "Currency", None, 110))

	invalid = {quotation.name for quotation in quotations if discarded(quotation)}
	lines = {}
	for item in items:
		key = item.item_code or (item.description or "").strip().lower()
		if not key:
			continue
		line = lines.setdefault(
			key,
			frappe._dict(
				item_name=item.item_name or item.item_code or item.description,
				description=item.description,
				qty=item.qty,
				_metric_values={"rate": [], "global": []},
				lowest_fields=[],
			),
		)
		qfields = fields_of[item.parent]
		valid_quotation = item.parent not in invalid

		line[qfields["rate"]] = flt(item.rate)
		if valid_quotation:
			line._metric_values["rate"].append((flt(item.rate), qfields["rate"]))

		if qfields["global"]:
			line[qfields["global"]] = flt(item.amount)
			if valid_quotation:
				line._metric_values["global"].append((flt(item.amount), qfields["global"]))

	def _lowest_fields(values):
		"""(valor, fieldname) pares válidos (>0) -> lista de fieldnames com o menor valor."""
		valid = [(value, fieldname) for value, fieldname in values if value > 0]
		if not valid:
			return None, []
		lowest = min(value for value, _ in valid)
		return lowest, [fieldname for value, fieldname in valid if value == lowest]

	rows = []
	for line in lines.values():
		metric_values = line.pop("_metric_values")
		lowest_fields = []

		# a coluna de resumo "Média" só considera o preço unitário
		rate_lowest, rate_fields = _lowest_fields(metric_values["rate"])
		if rate_lowest is not None:
			valid_prices = [value for value, _ in metric_values["rate"] if value > 0]
			line.average = sum(valid_prices) / len(valid_prices)
			lowest_fields += rate_fields

		_, fields = _lowest_fields(metric_values["global"])
		lowest_fields += fields

		line.lowest_fields = lowest_fields
		rows.append(line)

	global_totals = {}
	for item in items:
		global_totals[item.parent] = global_totals.get(item.parent, 0) + flt(item.amount)

	grand_total_row = frappe._dict(
		item_name=frappe._("TOTAL GERAL"), description=None, is_total=1, lowest_fields=[]
	)
	for quotation in quotations:
		qfields = fields_of[quotation.name]
		grand_total_row[qfields["rate"]] = flt(quotation.grand_total)
		if qfields["global"]:
			grand_total_row[qfields["global"]] = global_totals.get(quotation.name, 0)

	valid_quotations = [quotation for quotation in quotations if not discarded(quotation)]
	valid_totals = [flt(quotation.grand_total) for quotation in valid_quotations]
	total_lowest_fields = []
	if valid_totals:
		lowest_total = min(valid_totals)
		total_lowest_fields += [
			fields_of[quotation.name]["rate"]
			for quotation in valid_quotations
			if flt(quotation.grand_total) == lowest_total
		]

	if show_global and valid_quotations:
		lowest_global = min(global_totals.get(q.name, 0) for q in valid_quotations)
		total_lowest_fields += [
			fields_of[q.name]["global"]
			for q in valid_quotations
			if global_totals.get(q.name, 0) == lowest_global
		]

	grand_total_row.lowest_fields = total_lowest_fields
	rows.append(grand_total_row)

	report_summary = [summary("Propostas comparadas", len(quotations))]
	if valid_totals:
		lowest = min(valid_totals)
		winner = next(q for q in valid_quotations if flt(q.grand_total) == lowest)
		report_summary += [
			summary("Menor valor global", lowest, "Currency", "green"),
			summary("Menor proposta", winner.supplier_name or winner.supplier, "Data"),
			summary("Média das propostas", sum(valid_totals) / len(valid_totals), "Currency"),
		]
	return columns, rows, None, None, report_summary


def _base_columns(include_description=False):
	columns = [col("Serviço", "item_name", "Data", None, 200)]
	if include_description:
		columns.append(col("Descrição", "description", "Small Text", None, 240))
	columns.append(col("Qtd.", "qty", "Float", None, 70))
	return columns
