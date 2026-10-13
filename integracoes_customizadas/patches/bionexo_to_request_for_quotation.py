import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

MR_REMOVED_FIELDS = [
	"custom_bionexo",
	"custom_id_cotacao",
	"custom_column_break_ld2uf",
	"custom_link_bionexo",
]


def execute():
	"""Move a integração Bionexo do Material Request para a Request for Quotation."""
	_remove_material_request_bionexo()
	_customize_request_for_quotation()
	frappe.clear_cache()


def _remove_material_request_bionexo():
	frappe.delete_doc("Client Script", "Botão de Exportação em XML", force=True, ignore_missing=True)

	for fieldname in MR_REMOVED_FIELDS:
		frappe.delete_doc(
			"Custom Field", f"Material Request-{fieldname}", force=True, ignore_missing=True
		)
	frappe.delete_doc(
		"Property Setter",
		"Material Request-custom_id_cotacao-in_list_view",
		force=True,
		ignore_missing=True,
	)

	# A seção "Dados do Paciente" ficava após o último campo Bionexo.
	frappe.db.set_value(
		"Custom Field",
		"Material Request-custom_dados_do_paciente",
		"insert_after",
		"custom_numeracao_antiga",
	)

	_drop_from_field_order("Material Request", MR_REMOVED_FIELDS)


def _drop_from_field_order(doctype, fieldnames):
	name = f"{doctype}-main-field_order"
	value = frappe.db.get_value("Property Setter", name, "value")
	if not value:
		return
	order = [f for f in json.loads(value) if f not in fieldnames]
	frappe.db.set_value("Property Setter", name, "value", json.dumps(order))


def _customize_request_for_quotation():
	make_property_setter("Request for Quotation", "suppliers", "reqd", 0, "Check")

	create_custom_fields(
		{
			"Request for Quotation": [
				{
					"fieldname": "custom_id_bionexo",
					"label": "ID Bionexo",
					"fieldtype": "Data",
					"insert_after": "custom_tipo_de_contratacao",
				},
				{
					"fieldname": "custom_link_bionexo",
					"label": "Link Bionexo",
					"fieldtype": "Data",
					"options": "URL",
					"insert_after": "custom_id_bionexo",
				},
			]
		},
		update=True,
	)

	name = "Request for Quotation-main-field_order"
	value = frappe.db.get_value("Property Setter", name, "value")
	if value:
		order = json.loads(value)
		if "custom_id_bionexo" not in order:
			i = order.index("custom_tipo_de_contratacao") + 1 if "custom_tipo_de_contratacao" in order else len(order)
			order[i:i] = ["custom_id_bionexo", "custom_link_bionexo"]
			frappe.db.set_value("Property Setter", name, "value", json.dumps(order))
