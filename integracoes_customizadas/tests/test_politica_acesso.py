# Copyright (c) 2026, StillPulse and contributors
# For license information, please see license.txt
import frappe
from frappe.tests.utils import FrappeTestCase

from integracoes_customizadas.politicas.acesso_doctypes import (
	doctypes_dos_apps_customizados,
	modulos_do_app,
	verificar,
)
from integracoes_customizadas.politicas.atalhos import ATALHOS, garantir_atalhos

MODULOS_DO_APP = {"Integracoes Customizadas", "Provas", "Juridico"}


class TestPoliticaAcesso(FrappeTestCase):
	def test_todo_doctype_customizado_tem_atalho_e_leitor(self):
		problemas = verificar()
		self.assertEqual(
			{tipo: itens for tipo, itens in problemas.items() if itens},
			{},
			"DocTypes sem local de acesso adequado: adicione-os a um Workspace e dê leitura a um papel.",
		)

	def test_verificacao_varre_apenas_os_modulos_deste_app(self):
		self.assertEqual(set(modulos_do_app()), MODULOS_DO_APP)
		doctypes = doctypes_dos_apps_customizados()
		self.assertTrue(doctypes)
		self.assertEqual({d.module for d in doctypes} - MODULOS_DO_APP, set())
		nomes = {d.name for d in doctypes}
		# DocTypes de outros apps (hrms, erpnext, clm, rh_brasil) ficam de fora e são fiscalizados nos donos.
		self.assertFalse(nomes & {"Employee", "Item", "Canal de Denuncias", "CBO"})
		self.assertIn("Processo Judicial", nomes)
		self.assertIn("Edital", nomes)

	def test_atalhos_cobrem_os_doctypes_do_app_e_sao_idempotentes(self):
		for _card, itens, _candidatos in ATALHOS:
			for _rotulo, doctype in itens:
				self.assertTrue(frappe.db.exists("DocType", doctype), doctype)
		garantir_atalhos()
		self.assertEqual(garantir_atalhos(), {})
