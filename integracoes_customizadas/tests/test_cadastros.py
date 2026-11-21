# Copyright (c) 2026, StillPulse and contributors
# For license information, please see license.txt
"""Cadastros de produção instalados pelo app: existem, seguem o definido e nunca sobrescrevem o que já há."""

import frappe
from frappe.tests.utils import FrappeTestCase

from integracoes_customizadas.cadastros.instalacao import (
	ARQUIVOS,
	carregar_definicao,
	garantir_cadastros,
	garantir_doctype,
)

# Política de acesso do Canal de Denuncias (sensível), igual à de produção: só estes papéis.
PAPEIS_CANAL = {"System Manager", "HR Manager", "HR User"}


class TestCadastros(FrappeTestCase):
	def test_doctypes_existem_e_sao_custom(self):
		for arquivo in ARQUIVOS:
			nome = carregar_definicao(arquivo)["name"]
			self.assertEqual(frappe.db.get_value("DocType", nome, "custom"), 1, nome)

	def test_garantir_e_idempotente(self):
		self.assertEqual(garantir_cadastros(), [])

	def test_nao_sobrescreve_doctype_existente(self):
		definicao = carregar_definicao("cbo")
		original = frappe.db.get_value("DocType", "CBO", "title_field")
		frappe.db.set_value("DocType", "CBO", "title_field", "cod_ocupacao", update_modified=False)
		try:
			self.assertFalse(garantir_doctype(definicao))
			self.assertEqual(frappe.db.get_value("DocType", "CBO", "title_field"), "cod_ocupacao")
		finally:
			frappe.db.set_value("DocType", "CBO", "title_field", original, update_modified=False)

	def test_canal_de_denuncias_so_para_rh_e_administrador(self):
		definicao = carregar_definicao("canal_de_denuncias")
		self.assertEqual({p["role"] for p in definicao["permissions"]}, PAPEIS_CANAL)
		papeis = set(frappe.get_all("DocPerm", filters={"parent": "Canal de Denuncias"}, pluck="role"))
		papeis |= set(
			frappe.get_all("Custom DocPerm", filters={"parent": "Canal de Denuncias"}, pluck="role")
		)
		self.assertEqual(papeis, PAPEIS_CANAL)
		self.assertIn("Colaboradores Link", {f.options for f in frappe.get_meta("Canal de Denuncias").fields})

	def test_definicoes_nao_trazem_dados_de_pessoas(self):
		for arquivo in ARQUIVOS:
			definicao = carregar_definicao(arquivo)
			self.assertEqual(definicao["doctype"], "DocType")
			self.assertNotIn("owner", definicao)
			self.assertNotIn("@", str(definicao))

	def test_campo_item_bionexo_segue_producao(self):
		campo = frappe.get_meta("Item").get_field("custom_código_bionexo")
		self.assertEqual(campo.label, "Código Bionexo")
		self.assertEqual(campo.insert_after, "stock_uom")
		self.assertEqual(campo.hidden, 1)
