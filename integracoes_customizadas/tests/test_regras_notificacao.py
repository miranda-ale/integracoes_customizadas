"""Regras de notificação: 10+ variantes no WhatsApp e e-mail no layout institucional (manifesto do clm, 6 e 7a)."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from integracoes_customizadas import email_institucional
from integracoes_customizadas.seed.variantes_modelos import VARIANTES
from integracoes_customizadas.whatsapp import notification
from integracoes_customizadas.whatsapp.modelos import completar_variantes, variantes_ativas
from integracoes_customizadas.whatsapp.roteador import MIN_VARIANTES

CONVOCACAO = "Convocação de Reunião de Comissão"


def _modelo(titulo="Modelo de teste", variantes=0, ativo=1):
	return frappe.get_doc(
		{
			"doctype": "Modelo WhatsApp",
			"titulo": titulo,
			"ativo": ativo,
			"mensagem": "Olá, {{ doc.name }}",
			"variantes": [
				{"mensagem": f"Oi {i}, {{{{ doc.name }}}}", "ativo": 1, "peso": 1} for i in range(variantes)
			],
		}
	)


class TestVariantesMinimas(FrappeTestCase):
	def test_sementes_tem_ao_menos_dez_variantes(self):
		for titulo, textos in VARIANTES.items():
			self.assertGreaterEqual(len(set(textos)), MIN_VARIANTES, titulo)

	def test_modelo_ativo_com_menos_de_dez_variantes_nao_salva(self):
		with self.assertRaises(frappe.ValidationError):
			_modelo(variantes=MIN_VARIANTES - 1).validar_minimo_de_variantes()
		_modelo(variantes=MIN_VARIANTES).validar_minimo_de_variantes()
		_modelo(variantes=0, ativo=0).validar_minimo_de_variantes()

	def test_variante_inativa_nao_conta(self):
		modelo = _modelo(variantes=MIN_VARIANTES)
		modelo.variantes[0].ativo = 0
		with self.assertRaises(frappe.ValidationError):
			modelo.validar_minimo_de_variantes()

	def test_completar_usa_as_sementes_do_titulo_sem_duplicar(self):
		modelo = _modelo(CONVOCACAO)
		modelo.append("variantes", {"mensagem": VARIANTES[CONVOCACAO][0], "ativo": 1, "peso": 1})
		self.assertEqual(completar_variantes(modelo), len(VARIANTES[CONVOCACAO]) - 1)
		self.assertGreaterEqual(len(variantes_ativas(modelo)), MIN_VARIANTES)
		self.assertEqual(completar_variantes(modelo), 0)

	def test_completar_nao_mexe_em_modelo_sem_semente(self):
		modelo = _modelo(variantes=2)
		self.assertEqual(completar_variantes(modelo), 0)
		self.assertEqual(len(modelo.variantes), 2)

	def test_notification_de_whatsapp_exige_modelo(self):
		alert = frappe.get_doc({"doctype": "Notification", "send_whatsapp": 1, "modelo_whatsapp": None})
		with self.assertRaises(frappe.ValidationError):
			alert.validar_modelo_whatsapp()


class TestEmailInstitucional(FrappeTestCase):
	def test_corpo_sem_clm_mantem_fatos_botao_e_nota(self):
		with patch.object(email_institucional, "_render_email", return_value=None):
			html = email_institucional.corpo(
				"T", "<p>x</p>", fatos=[("Edital", "<b>E1</b>")], acao=("Abrir", "https://x.test"), nota="n"
			)
		self.assertIn("&lt;b&gt;E1&lt;/b&gt;", html)
		self.assertIn("https://x.test", html)
		self.assertIn("<p>x</p>", html)

	def test_email_da_notification_vai_no_layout_institucional(self):
		if "clm" not in frappe.get_installed_apps():
			self.skipTest("clm não instalado")
		alert = frappe._dict(
			name="Regra",
			subject="Aviso {{ doc.name }}",
			message="<p>Corpo {{ doc.name }}</p>",
			message_type="HTML",
		)
		doc = frappe.get_doc({"doctype": "ToDo", "name": "TD-1", "description": "x"})
		html = notification.corpo_do_email(alert, doc, {"doc": doc})
		self.assertTrue(email_institucional.ja_institucional(html))
		self.assertIn("Corpo TD-1", html)
		self.assertIn("Abrir documento", html)
		self.assertIsNone(notification.corpo_do_email(frappe._dict(alert, message=html), doc, {"doc": doc}))
