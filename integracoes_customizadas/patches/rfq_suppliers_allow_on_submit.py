from frappe.custom.doctype.property_setter.property_setter import make_property_setter
import frappe


def execute():
	"""Mantém a tabela de fornecedores da RFQ visível e editável após o envio."""
	make_property_setter("Request for Quotation", "suppliers", "allow_on_submit", 1, "Check")
	for fieldname in ("supplier_name", "email_id"):
		make_property_setter(
			"Request for Quotation Supplier", fieldname, "allow_on_submit", 1, "Check"
		)
	frappe.clear_cache()
