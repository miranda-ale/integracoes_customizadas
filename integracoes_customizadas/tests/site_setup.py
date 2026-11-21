# Copyright (c) 2026, Alessandro Miranda and contributors
# For license information, please see license.txt

"""Prepara um site novo (CI) com stubs dos DocTypes que os Custom Fields do fixture referenciam.

Os Custom Fields de `Employee` e `Designation` apontam para os DocTypes `Municipios`, `CBO` e `Dependentes`,
que não pertencem a este app (em produção foram criados à mão). Sem eles, a criação dos test records do hrms
falha com `WrongOptionsDoctypeLinkError`. Não é chamado por hook e não altera sites de produção. Idempotente.
"""

from __future__ import annotations

import frappe

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
				"module": "Integracoes Customizadas",
				"custom": 1,
				"istable": 1 if eh_tabela else 0,
				"autoname": "" if eh_tabela else "Prompt",
				"fields": [{"fieldname": "descricao", "fieldtype": "Data", "label": "Descricao"}],
				"permissions": [] if eh_tabela else [{"role": "System Manager", "read": 1}],
			}
		).insert(ignore_permissions=True)
	frappe.db.commit()
