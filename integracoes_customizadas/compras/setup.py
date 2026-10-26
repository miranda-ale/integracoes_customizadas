# Copyright (c) 2026, BHCL and contributors
# For license information, please see license.txt
"""Metadados do fluxo de recebimento de compras (idempotente, roda a cada migrate).

Custom Fields da NF no Purchase Receipt, seções de impostos recolhidas por padrão (PR, PO e PI) e o layout enxuto dos
Workspaces Buying e Stock (`compras/workspaces.py`). Nenhum papel novo: o Stock User já cria/submete Purchase
Receipt e lê Purchase Order, e criar Custom DocPerm substituiria todas as permissões padrão do DocType.
"""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from integracoes_customizadas.compras.workspaces import aplicar_layouts

NF_FIELDS = {
	"Purchase Receipt": [
		{
			"fieldname": "custom_compras_nf_section",
			"fieldtype": "Section Break",
			"label": "Nota Fiscal do Fornecedor",
			"insert_after": "return_against",
		},
		{
			"fieldname": "custom_compras_nf_numero",
			"fieldtype": "Data",
			"label": "Número da NF",
			"allow_on_submit": 1,
			"in_standard_filter": 1,
			"insert_after": "custom_compras_nf_section",
		},
		{
			"fieldname": "custom_compras_nf_serie",
			"fieldtype": "Data",
			"label": "Série",
			"allow_on_submit": 1,
			"insert_after": "custom_compras_nf_numero",
		},
		{
			"fieldname": "custom_compras_nf_chave",
			"fieldtype": "Data",
			"label": "Chave de Acesso da NF-e",
			"description": "44 caracteres, como no DANFE. Preenche número e série automaticamente.",
			"allow_on_submit": 1,
			"insert_after": "custom_compras_nf_serie",
		},
		{
			"fieldname": "custom_compras_nf_col",
			"fieldtype": "Column Break",
			"insert_after": "custom_compras_nf_chave",
		},
		{
			"fieldname": "custom_compras_nf_data",
			"fieldtype": "Date",
			"label": "Data de Emissão da NF",
			"allow_on_submit": 1,
			"insert_after": "custom_compras_nf_col",
		},
		{
			"fieldname": "custom_compras_nf_valor",
			"fieldtype": "Currency",
			"label": "Valor Total da NF",
			"options": "currency",
			"allow_on_submit": 1,
			"insert_after": "custom_compras_nf_data",
		},
		{
			"fieldname": "custom_compras_nf_anexo",
			"fieldtype": "Attach",
			"label": "Anexo da NF (PDF/XML)",
			"allow_on_submit": 1,
			"insert_after": "custom_compras_nf_valor",
		},
	]
}

# Seções de impostos que ficam recolhidas ao abrir (como "Desconto Adicional"): {doctype: [(fieldname, rótulo novo ou None)]}.
# No Purchase Receipt os impostos ocupam duas seções; no Purchase Order e na Purchase Invoice, uma só.
SECOES_RECOLHIDAS = {
	"Purchase Receipt": [("taxes_charges_section", None), ("taxes_section", "Taxes and Charges Detail")],
	"Purchase Order": [("taxes_section", None)],
	"Purchase Invoice": [("taxes_section", None)],
}


def garantir_campos_nf():
	create_custom_fields(NF_FIELDS, update=True)


def garantir_secoes_recolhidas():
	for doctype, secoes in SECOES_RECOLHIDAS.items():
		for fieldname, rotulo in secoes:
			make_property_setter(
				doctype, fieldname, "collapsible", 1, "Check", validate_fields_for_doctype=False
			)
			if rotulo:
				make_property_setter(
					doctype, fieldname, "label", rotulo, "Data", validate_fields_for_doctype=False
				)


def after_migrate():
	garantir_campos_nf()
	garantir_secoes_recolhidas()
	aplicar_layouts()
