# Copyright (c) 2026, Alessandro Miranda and contributors
# For license information, please see license.txt

"""Prepara um site novo (CI) com o que em produção foi criado à mão e o app não instala.

Stubs dos DocTypes que os Custom Fields do fixture referenciam e o Custom Field `Item.custom_código_bionexo`
(usado por `importacao_bionexo.py` e pelos testes de importação) e os Custom Fields do RFQ `custom_id_bionexo` e
`custom_link_bionexo` e o Property Setter que torna `suppliers` opcional no RFQ (criados em produção pelo patch
`bionexo_to_request_for_quotation`).

Os Custom Fields de `Employee` e `Designation` apontam para os DocTypes `Municipios`, `CBO` e `Dependentes`,
que não pertencem a este app (em produção foram criados à mão). Sem eles, a criação dos test records do hrms
falha com `WrongOptionsDoctypeLinkError`. Não é chamado por hook e não altera sites de produção. Idempotente.
"""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

# nome -> eh tabela filha
DOCTYPES_STUB = {"Municipios": False, "CBO": False, "Dependentes": True}


def criar_doctypes_stub():
	for nome, eh_tabela in DOCTYPES_STUB.items():
		if frappe.db.exists("DocType", nome):
			continue
		frappe.get_doc(
			{
				"doctype": "DocType",
				"name": nome,
				"module": "Custom",
				"custom": 1,
				"istable": 1 if eh_tabela else 0,
				"autoname": "" if eh_tabela else "Prompt",
				"fields": [{"fieldname": "descricao", "fieldtype": "Data", "label": "Descricao"}],
				"permissions": [] if eh_tabela else [{"role": "System Manager", "read": 1}],
			}
		).insert(ignore_permissions=True)
	create_custom_fields(
		{
			"Item": [{"fieldname": "custom_código_bionexo", "label": "Código Bionexo", "fieldtype": "Data"}],
			# In production these two come from patch bionexo_to_request_for_quotation, which does not run on a new site.
			"Request for Quotation": [
				{"fieldname": "custom_id_bionexo", "label": "ID Bionexo", "fieldtype": "Data"},
				{
					"fieldname": "custom_link_bionexo",
					"label": "Link Bionexo",
					"fieldtype": "Data",
					"options": "URL",
				},
			],
		},
		update=False,
	)
	# Also from that patch: the Bionexo import creates the RFQ before the suppliers are known.
	make_property_setter("Request for Quotation", "suppliers", "reqd", 0, "Check")
	frappe.db.commit()
