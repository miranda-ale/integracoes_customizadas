from unittest.mock import patch
from xml.etree.ElementTree import fromstring
from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase

from integracoes_customizadas.bionexo.export_xml import export_request_for_quotation_bionexo_xml


class TestBionexoExport(FrappeTestCase):
	def test_request_for_quotation_header_uses_its_source_references(self):
		document = SimpleNamespace(
			name="REQ-ORC-0001",
			docstatus=1,
			schedule_date="2026-10-15",
			terms="<p>Condições</p>",
			items=[SimpleNamespace(item_code="SERV-001", qty=2, idx=1, material_request="MAT-REQ-001")],
		)
		frappe.local.response = {}

		with patch("integracoes_customizadas.bionexo.export_xml.frappe.get_doc", return_value=document):
			export_request_for_quotation_bionexo_xml(document.name)

		xml = fromstring(frappe.response["filecontent"])
		header = xml.find("Cabecalho")
		self.assertEqual(header.findtext("Requisicao"), "MAT-REQ-001")
		self.assertEqual(header.findtext("Titulo_Pdc"), document.name)
		self.assertEqual(header.findtext("Data_Vencimento"), "15/10/2026")
		self.assertEqual(header.findtext("Hora_Vencimento"), "14:00")
		self.assertEqual(header.findtext("Campo_Extra/Nome"), "registro_interno_ERP")
		self.assertEqual(header.findtext("Campo_Extra/Valor"), "MAT-REQ-001")
		self.assertIsNone(xml.find("Campo_Extra"))
