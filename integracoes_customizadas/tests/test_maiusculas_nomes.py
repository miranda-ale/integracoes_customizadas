import frappe
from frappe.tests.utils import FrappeTestCase

from integracoes_customizadas.normalizacao.maiusculas import normalizar


class TestMaiusculasNomes(FrappeTestCase):
	def test_normalizar_remove_acento_e_espacos(self):
		self.assertEqual(normalizar("  josé   da  Conceição "), "JOSE DA CONCEICAO")

	def test_normalizar_idempotente(self):
		self.assertEqual(normalizar(normalizar("ação")), "ACAO")

	def test_item_name_em_caixa_alta(self):
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "TESTE-MAIUSCULA-001",
				"item_name": "luva de procedimento é",
				"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
				"stock_uom": frappe.db.get_value("UOM", {}, "name"),
			}
		).insert()
		self.assertEqual(item.item_name, "LUVA DE PROCEDIMENTO E")

	def test_supplier_name_em_caixa_alta(self):
		s = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": "fornecedor ágil ltda",
				"tax_id": "11222333000181",
				"supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0}, "name"),
			}
		).insert()
		self.assertEqual(s.supplier_name, "FORNECEDOR AGIL LTDA")

	def test_campo_fora_da_allowlist_intacto(self):
		c = frappe.get_doc(
			{"doctype": "Contact", "first_name": "maria", "email_ids": [{"email_id": "Maria@x.com"}]}
		).insert()
		self.assertEqual(c.first_name, "MARIA")
		self.assertEqual(c.email_ids[0].email_id, "Maria@x.com")
