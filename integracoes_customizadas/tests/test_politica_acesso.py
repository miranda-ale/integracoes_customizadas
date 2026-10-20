# Copyright (c) 2026, StillPulse and contributors
# For license information, please see license.txt
from frappe.tests.utils import FrappeTestCase

from integracoes_customizadas.politicas.acesso_doctypes import verificar


class TestPoliticaAcesso(FrappeTestCase):
	def test_todo_doctype_customizado_tem_atalho_e_leitor(self):
		problemas = verificar()
		self.assertEqual(
			{tipo: itens for tipo, itens in problemas.items() if itens},
			{},
			"DocTypes sem local de acesso adequado: adicione-os a um Workspace e dê leitura a um papel.",
		)
