# Copyright (c) 2026, BHCL and contributors
# For license information, please see license.txt
#
# Purchase Orders still waiting for goods, for the unit that receives them. Uses get_list, so User Permissions
# (Company, Warehouse, ...) already limit each unit to its own orders.

import frappe
from frappe import _
from frappe.utils import date_diff, flt, nowdate

CLOSED_STATUSES = ("Closed", "Completed", "Cancelled")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	query = [
		["Purchase Order", "docstatus", "=", 1],
		["Purchase Order", "per_received", "<", 100],
		["Purchase Order", "status", "not in", CLOSED_STATUSES],
	]
	for field in ("company", "supplier"):
		if filters.get(field):
			query.append(["Purchase Order", field, "=", filters[field]])
	if filters.get("from_date"):
		query.append(["Purchase Order", "transaction_date", ">=", filters["from_date"]])
	orders = frappe.get_list(
		"Purchase Order",
		filters=query,
		fields=[
			"name",
			"supplier_name",
			"company",
			"set_warehouse",
			"transaction_date",
			"schedule_date",
			"per_received",
			"grand_total",
			"status",
			"currency",
		],
		order_by="schedule_date asc, transaction_date asc",
		limit_page_length=0,
	)
	com_estoque = _com_item_de_estoque([o.name for o in orders])
	today = nowdate()
	data = []
	for order in orders:
		if order.name not in com_estoque:
			continue
		atraso = max(date_diff(today, order.schedule_date), 0) if order.schedule_date else 0
		if filters.get("somente_atrasados") and not atraso:
			continue
		data.append(
			{
				"purchase_order": order.name,
				"supplier_name": order.supplier_name,
				"company": order.company,
				"warehouse": order.set_warehouse,
				"transaction_date": order.transaction_date,
				"schedule_date": order.schedule_date,
				"atraso": atraso,
				"per_received": flt(order.per_received),
				"grand_total": order.grand_total,
				"status": _(order.status),
				"acao": "Receber",
			}
		)
	atrasados = sum(1 for row in data if row["atraso"])
	return _columns(), data, None, None, _summary(len(data), atrasados)


def _com_item_de_estoque(names):
	"""Orders with at least one stock item: service-only orders are never received physically."""
	if not names:
		return set()
	rows = frappe.db.sql(
		"""select distinct poi.parent from `tabPurchase Order Item` poi
		join `tabItem` i on i.name = poi.item_code
		where i.is_stock_item = 1 and poi.parent in %(names)s""",
		{"names": names},
	)
	return {r[0] for r in rows}


def _columns():
	return [
		{
			"label": _("Pedido"),
			"fieldname": "purchase_order",
			"fieldtype": "Link",
			"options": "Purchase Order",
			"width": 150,
		},
		{"label": _("Fornecedor"), "fieldname": "supplier_name", "fieldtype": "Data", "width": 220},
		{
			"label": _("Empresa"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 170,
		},
		{
			"label": _("Armazém"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 160,
		},
		{"label": _("Emissão"), "fieldname": "transaction_date", "fieldtype": "Date", "width": 100},
		{"label": _("Entrega prevista"), "fieldname": "schedule_date", "fieldtype": "Date", "width": 120},
		{"label": _("Atraso (dias)"), "fieldname": "atraso", "fieldtype": "Int", "width": 100},
		{"label": _("% Recebido"), "fieldname": "per_received", "fieldtype": "Percent", "width": 100},
		{"label": _("Valor"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 120},
		{"label": _("Situação"), "fieldname": "status", "fieldtype": "Data", "width": 130},
		{"label": _("Ação"), "fieldname": "acao", "fieldtype": "Data", "width": 90},
	]


def _summary(total, atrasados):
	return [
		{"label": _("Pedidos a receber"), "value": total, "datatype": "Int"},
		{
			"label": _("Com entrega atrasada"),
			"value": atrasados,
			"datatype": "Int",
			"indicator": "red" if atrasados else "green",
		},
	]
