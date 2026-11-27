# Copyright (c) 2026, BHCL and contributors
# For license information, please see license.txt
import json

import frappe
from frappe.tests.utils import FrappeTestCase

from integracoes_customizadas.compras import workspaces


class TestWorkspacesCompras(FrappeTestCase):
	def setUp(self):
		workspaces.aplicar_layouts()

	def test_links_e_atalhos_sao_exatamente_os_declarados(self):
		for nome in workspaces.LAYOUTS:
			links, shortcuts, _content = workspaces.montar(nome)
			ws = frappe.get_doc("Workspace", nome)
			self.assertEqual(
				[(l.type, l.label, l.link_to if l.type == "Link" else None) for l in ws.links],
				[(l["type"], l["label"], l.get("link_to")) for l in links],
			)
			self.assertEqual([s.label for s in ws.shortcuts], [s["label"] for s in shortcuts])
			self.assertEqual((len(ws.number_cards), len(ws.charts)), (0, 0))

	def test_conteudo_casa_com_cards_e_atalhos(self):
		for nome in workspaces.LAYOUTS:
			ws = frappe.get_doc("Workspace", nome)
			blocos = json.loads(ws.content)
			cards = {l.label for l in ws.links if l.type == "Card Break"}
			atalhos = {s.label for s in ws.shortcuts}
			self.assertEqual({b["data"]["card_name"] for b in blocos if b["type"] == "card"}, cards)
			self.assertEqual({b["data"]["shortcut_name"] for b in blocos if b["type"] == "shortcut"}, atalhos)
			# No link outside a card: the first row is always a Card Break.
			self.assertEqual(ws.links[0].type, "Card Break")

	def test_todos_os_alvos_existem(self):
		for nome in workspaces.LAYOUTS:
			ws = frappe.get_doc("Workspace", nome)
			for l in ws.links:
				if l.type == "Link":
					self.assertTrue(frappe.db.exists(l.link_type, l.link_to), f"{nome}: {l.link_to}")
			for s in ws.shortcuts:
				self.assertTrue(frappe.db.exists(s.type, s.link_to), f"{nome}: {s.link_to}")

	def test_reaplicar_nao_altera_o_workspace(self):
		antes = {n: frappe.db.get_value("Workspace", n, "modified") for n in workspaces.LAYOUTS}
		self.assertEqual(workspaces.aplicar_layouts(), [])
		self.assertEqual(
			antes, {n: frappe.db.get_value("Workspace", n, "modified") for n in workspaces.LAYOUTS}
		)

	def test_bionexo_continua_em_compras(self):
		ws = frappe.get_doc("Workspace", "Buying")
		self.assertIn("Importacao Bionexo", {l.link_to for l in ws.links})

	def test_documentos_de_fornecedor_no_compras(self):
		if not frappe.db.exists("DocType", "CLM Supplier Document"):
			self.skipTest("clm não instalado")
		alvos = {l.link_to for l in frappe.get_doc("Workspace", "Buying").links}
		self.assertIn("CLM Supplier Document", alvos)
		self.assertIn("CLM Documentos de Fornecedor a Vencer", alvos)
