# Copyright (c) 2026, Alessandro Miranda and contributors
# For license information, please see license.txt

"""Prepara um site novo (CI) com os DocTypes que em produção foram criados à mão e o app não instala.

Os Custom Fields de `Employee` e `Designation` apontam para os DocTypes `Municipios`, `CBO` e `Dependentes`,
e o workspace Jurídico tem um card para `Canal de Denuncias`; nenhum deles pertence a um app do grupo. Sem
eles, a criação dos test records do hrms falha com `WrongOptionsDoctypeLinkError` e o card Ética some do
workspace. São stubs mínimos, só de teste: não é chamado por hook e não altera sites de produção. Idempotente.
Remover um stub daqui exige antes incluir o DocType real no app (issue #8).
"""

from __future__ import annotations

import frappe

# nome -> eh tabela filha
DOCTYPES_STUB = {"Municipios": False, "CBO": False, "Dependentes": True, "Canal de Denuncias": False}


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
	frappe.db.commit()
