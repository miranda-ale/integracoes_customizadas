# Copyright (c) 2026, Alessandro Miranda and contributors
# For license information, please see license.txt

"""Preparo do site de teste (CI). Não é chamado por hook e não altera sites de produção.

Os Custom Fields de `Designation` do fixture (`custom_área`, `custom_cbo`, `custom_escolaridade` e
`custom_descrição_detalhada_das_atividades`) são obrigatórios em produção, e é isso que se quer manter. Os test
records de `Designation` do hrms/erpnext não os preenchem, então a criação deles falha com `MandatoryError`. Aqui a
obrigatoriedade é relaxada SÓ no site de teste (campo e metadados em cache); `fixtures/custom_field.json` não muda.
Deve rodar depois do `bench migrate`, que sincroniza os fixtures e reaplica `reqd=1`. Idempotente.
"""

from __future__ import annotations

import frappe


def relaxar_obrigatoriedade_designation() -> list[str]:
	"""Zera `reqd` dos Custom Fields obrigatórios de Designation (somente no site em que roda)."""
	campos = frappe.get_all("Custom Field", filters={"dt": "Designation", "reqd": 1}, pluck="name")
	for nome in campos:
		frappe.db.set_value("Custom Field", nome, "reqd", 0, update_modified=False)
	frappe.db.commit()
	frappe.clear_cache(doctype="Designation")
	return campos
