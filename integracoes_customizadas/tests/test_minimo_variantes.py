import frappe
from frappe.tests.utils import FrappeTestCase

from integracoes_customizadas.whatsapp.modelos import variantes_ativas
from integracoes_customizadas.whatsapp.roteador import MIN_VARIANTES


class TestMinimoVariantes(FrappeTestCase):
	def test_todo_modelo_whatsapp_ativo_tem_10_variantes(self):
		for nome in frappe.get_all("Modelo WhatsApp", filters={"ativo": 1}, pluck="name"):
			modelo = frappe.get_doc("Modelo WhatsApp", nome)
			self.assertGreaterEqual(len(variantes_ativas(modelo)), MIN_VARIANTES, nome)

	def test_toda_notification_com_whatsapp_aponta_para_modelo(self):
		for n in frappe.get_all(
			"Notification", filters={"send_whatsapp": 1}, fields=["name", "modelo_whatsapp"]
		):
			self.assertTrue(n.modelo_whatsapp, n.name)
