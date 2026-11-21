# Copyright (c) 2026, StillPulse and contributors
# For license information, please see license.txt
"""Instalação limpa: os campos que a importação Bionexo usa existem sem depender de patches."""

import frappe
from frappe.tests.utils import FrappeTestCase

from integracoes_customizadas.bionexo.setup import garantir_campos_na_instalacao

CAMPOS = (
	("Request for Quotation", "custom_id_bionexo"),
	("Request for Quotation", "custom_link_bionexo"),
	("Item", "custom_código_bionexo"),
)


class TestInstalacaoBionexo(FrappeTestCase):
	def test_campos_existem_apos_a_instalacao(self):
		for doctype, campo in CAMPOS:
			self.assertTrue(frappe.get_meta(doctype).has_field(campo), f"{doctype}.{campo} ausente")

	def test_nao_sobrescreve_campo_existente(self):
		nome = "Request for Quotation-custom_id_bionexo"
		original = frappe.db.get_value("Custom Field", nome, "label")
		frappe.db.set_value("Custom Field", nome, "label", "Rótulo editado no site")
		try:
			garantir_campos_na_instalacao()
			self.assertEqual(frappe.db.get_value("Custom Field", nome, "label"), "Rótulo editado no site")
		finally:
			frappe.db.set_value("Custom Field", nome, "label", original)
