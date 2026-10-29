import json

import frappe
from frappe.tests.utils import FrappeTestCase

from integracoes_customizadas.juridico import indicadores, setup


class TestJuridicoIndicadores(FrappeTestCase):
	def test_dashboard_retorna_estrutura(self):
		dados = indicadores.get_dashboard()
		for chave in (
			"andamento",
			"encerrados",
			"total",
			"novos",
			"risco_alto",
			"sem_atualizacao",
			"assuntos",
		):
			self.assertIn(chave, dados)
		self.assertEqual(dados["total"], dados["andamento"] + dados["encerrados"])

	def test_dashboard_exige_leitura(self):
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				indicadores.get_dashboard()
		finally:
			frappe.set_user("Administrator")

	def test_workspace_tem_painel_e_atalho_de_pareceres(self):
		setup.ensure_indicadores_block()
		setup.ensure_juridico_workspace()
		content = json.loads(frappe.db.get_value("Workspace", setup.WORKSPACE, "content"))
		self.assertEqual(content[0]["id"], setup.INDICADORES_ID)
		if frappe.db.exists("DocType", setup.PARECERES_DOCTYPE):
			self.assertIn(setup.PARECERES_ID, [b.get("id") for b in content])

	def test_ensure_workspace_idempotente(self):
		setup.ensure_juridico_workspace()
		antes = frappe.db.get_value("Workspace", setup.WORKSPACE, "modified")
		setup.ensure_juridico_workspace()
		self.assertEqual(frappe.db.get_value("Workspace", setup.WORKSPACE, "modified"), antes)

	def test_permissoes_processo_judicial_vem_do_json(self):
		self.assertFalse(frappe.db.exists("Custom DocPerm", {"parent": "Processo Judicial"}))
		self.assertFalse(frappe.db.exists("DocPerm", {"parent": "Processo Judicial", "role": "HR User"}))
