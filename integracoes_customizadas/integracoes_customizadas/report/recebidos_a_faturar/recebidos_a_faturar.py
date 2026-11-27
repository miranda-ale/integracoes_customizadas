# Copyright (c) 2026, BHCL and contributors
# For license information, please see license.txt
#
# Submitted Purchase Receipts not fully invoiced yet, with the Nota Fiscal the unit registered on each one.

import frappe
from frappe import _
from frappe.utils import date_diff, flt, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	query = [
		["Purchase Receipt", "docstatus", "=", 1],
		["Purchase Receipt", "is_return", "=", 0],
		["Purchase Receipt", "per_billed", "<", 100],
	]
	for field in ("company", "supplier"):
		if filters.get(field):
			query.append(["Purchase Receipt", field, "=", filters[field]])
	if filters.get("somente_com_nf"):
		query.append(["Purchase Receipt", "custom_compras_nf_numero", "is", "set"])
	receipts = frappe.get_list(
		"Purchase Receipt",
		filters=query,
		fields=[
			"name",
			"supplier_name",
			"company",
			"posting_date",
			"grand_total",
			"per_billed",
			"custom_compras_nf_numero",
			"custom_compras_nf_serie",
			"custom_compras_nf_data",
			"custom_compras_nf_valor",
			"custom_compras_nf_anexo",
		],
		order_by="posting_date asc, name asc",
		limit_page_length=0,
	)
	today = nowdate()
	data = []
	for receipt in receipts:
		nf_valor = flt(receipt.custom_compras_nf_valor)
		data.append(
			{
				"purchase_receipt": receipt.name,
				"supplier_name": receipt.supplier_name,
				"company": receipt.company,
				"posting_date": receipt.posting_date,
				"dias": date_diff(today, receipt.posting_date),
				"nf_numero": receipt.custom_compras_nf_numero,
				"nf_serie": receipt.custom_compras_nf_serie,
				"nf_data": receipt.custom_compras_nf_data,
				"nf_valor": nf_valor or None,
				"grand_total": receipt.grand_total,
				"diferenca": (nf_valor - flt(receipt.grand_total)) if nf_valor else None,
				"nf_anexo": receipt.custom_compras_nf_anexo,
				"situacao_nf": "Informada" if receipt.custom_compras_nf_numero else "Pendente",
				"acao": "Criar Fatura",
			}
		)
	sem_nf = sum(1 for row in data if row["situacao_nf"] == "Pendente")
	summary = [
		{"label": _("Recebimentos a faturar"), "value": len(data), "datatype": "Int"},
		{
			"label": _("Sem Nota Fiscal informada"),
			"value": sem_nf,
			"datatype": "Int",
			"indicator": "red" if sem_nf else "green",
		},
	]
	return _columns(), data, None, None, summary


def _columns():
	return [
		{
			"label": _("Recebimento"),
			"fieldname": "purchase_receipt",
			"fieldtype": "Link",
			"options": "Purchase Receipt",
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
		{"label": _("Data do recebimento"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		{"label": _("Dias aguardando"), "fieldname": "dias", "fieldtype": "Int", "width": 110},
		{"label": _("Situação da NF"), "fieldname": "situacao_nf", "fieldtype": "Data", "width": 110},
		{"label": _("Nº da NF"), "fieldname": "nf_numero", "fieldtype": "Data", "width": 100},
		{"label": _("Série"), "fieldname": "nf_serie", "fieldtype": "Data", "width": 70},
		{"label": _("Emissão da NF"), "fieldname": "nf_data", "fieldtype": "Date", "width": 110},
		{"label": _("Valor da NF"), "fieldname": "nf_valor", "fieldtype": "Currency", "width": 120},
		{"label": _("Valor recebido"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 120},
		{"label": _("Diferença"), "fieldname": "diferenca", "fieldtype": "Currency", "width": 110},
		{"label": _("Anexo da NF"), "fieldname": "nf_anexo", "fieldtype": "Data", "width": 110},
		{"label": _("Ação"), "fieldname": "acao", "fieldtype": "Data", "width": 110},
	]
