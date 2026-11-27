# Copyright (c) 2026, BHCL and contributors
# For license information, please see license.txt
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from integracoes_customizadas.compras import process_view as pv
from integracoes_customizadas.compras import receipt


def doc(doctype, name, docstatus=1, **extra):
	return {"doctype": doctype, "name": name, "docstatus": docstatus, "restricted": 0, **extra}


def chain(**extra):
	"""MR -> PO -> PR -> PI, every document submitted unless overridden."""
	docs = {
		"Material Request": [doc("Material Request", "MR-1", status="Ordered", per_ordered=100)],
		"Purchase Order": [
			doc(
				"Purchase Order",
				"PO-1",
				status="To Receive and Bill",
				per_received=0,
				schedule_date="2026-01-10",
			)
		],
		"Purchase Receipt": [],
		"Purchase Invoice": [],
	}
	docs.update(extra)
	return docs


def by_key(stages):
	return {s["key"]: s for s in stages}


class TestComprasProcess(FrappeTestCase):
	def test_ordem_das_etapas(self):
		stages = pv.build_stages(chain(), today="2026-01-05")
		self.assertEqual(
			[s["key"] for s in stages], ["request", "rfq", "quotation", "order", "receipt", "invoice"]
		)
		stages = by_key(stages)
		for key in ("rfq", "quotation"):
			self.assertEqual((stages[key]["status"], stages[key]["optional"]), ("none", 1))

	def test_cotacao_forma_um_grupo_opcional(self):
		stages = by_key(pv.build_stages(chain(), today="2026-01-05"))
		self.assertEqual(
			{k: s["group"] for k, s in stages.items() if s["group"]},
			{"rfq": "cotacao", "quotation": "cotacao"},
		)
		self.assertEqual(stages["rfq"]["group_label"], "Cotação · opcional")
		self.assertIsNone(stages["order"]["group"])

	def test_rfq_enviado_sem_cotacao_aguarda_propostas(self):
		docs = chain(**{"Request for Quotation": [doc("Request for Quotation", "RFQ-1")]})
		stages = by_key(pv.build_stages(docs, today="2026-01-05"))
		self.assertEqual(stages["rfq"]["status"], "ok")
		self.assertEqual(stages["quotation"]["status"], "pending")
		self.assertIn("Aguardando propostas", stages["quotation"]["alerts"][0])

	def test_cotacao_sem_rfq_nao_exige_pedido_de_cotacao(self):
		docs = chain(**{"Supplier Quotation": [doc("Supplier Quotation", "SQ-1")]})
		stages = by_key(pv.build_stages(docs, today="2026-01-05"))
		self.assertEqual((stages["rfq"]["status"], stages["quotation"]["status"]), ("none", "ok"))

	def test_rfq_em_rascunho_fica_em_andamento(self):
		docs = chain(**{"Request for Quotation": [doc("Request for Quotation", "RFQ-1", docstatus=0)]})
		self.assertEqual(by_key(pv.build_stages(docs, today="2026-01-05"))["rfq"]["status"], "pending")

	def test_pedido_sem_recebimento_aguarda_e_alerta_atraso(self):
		em_dia = by_key(pv.build_stages(chain(), today="2026-01-05"))
		self.assertEqual(em_dia["order"]["status"], "ok")
		self.assertEqual(em_dia["receipt"]["status"], "pending")
		atrasado = by_key(pv.build_stages(chain(), today="2026-01-20"))["receipt"]
		self.assertEqual(atrasado["status"], "warn")
		self.assertIn("atrasada", atrasado["alerts"][0])

	def test_recebido_sem_nf_alerta_e_fatura_aguarda(self):
		docs = chain()
		docs["Purchase Order"][0].update(per_received=100)
		docs["Purchase Receipt"] = [
			doc("Purchase Receipt", "PR-1", per_billed=0, grand_total=100, is_return=0)
		]
		stages = by_key(pv.build_stages(docs, today="2026-01-05"))
		self.assertEqual(stages["receipt"]["status"], "warn")
		self.assertTrue(any("sem Nota Fiscal" in a for a in stages["receipt"]["alerts"]))
		self.assertEqual(stages["invoice"]["status"], "pending")
		self.assertIn("aguardando fatura (0 com NF", stages["invoice"]["alerts"][0])

	def test_cadeia_completa_fica_ok(self):
		docs = chain()
		docs["Purchase Order"][0].update(per_received=100, per_billed=100)
		docs["Purchase Receipt"] = [
			doc(
				"Purchase Receipt",
				"PR-1",
				per_billed=100,
				grand_total=100,
				is_return=0,
				custom_compras_nf_numero="123",
				custom_compras_nf_valor=100,
			)
		]
		docs["Purchase Invoice"] = [doc("Purchase Invoice", "PINV-1")]
		stages = pv.build_stages(docs, today="2026-01-05")
		self.assertEqual([s["status"] for s in stages if not s["optional"]], ["ok"] * 4)

	def test_valor_da_nf_divergente_alerta(self):
		docs = chain()
		docs["Purchase Order"][0].update(per_received=100)
		docs["Purchase Receipt"] = [
			doc(
				"Purchase Receipt",
				"PR-1",
				per_billed=0,
				grand_total=100,
				is_return=0,
				custom_compras_nf_numero="9",
				custom_compras_nf_valor=150,
			)
		]
		receipt_stage = by_key(pv.build_stages(docs, today="2026-01-05"))["receipt"]
		self.assertEqual(receipt_stage["status"], "warn")
		self.assertTrue(any("valor da NF" in a for a in receipt_stage["alerts"]))

	def test_cancelados_sao_ignorados(self):
		docs = chain()
		docs["Purchase Receipt"] = [doc("Purchase Receipt", "PR-X", docstatus=2, status="Cancelled")]
		stages = by_key(pv.build_stages(docs, today="2026-01-05"))
		self.assertEqual(stages["receipt"]["count"], 0)

	def test_restritos_so_sao_contados(self):
		docs = chain()
		docs["Purchase Invoice"] = [doc("Purchase Invoice", "PINV-1", restricted=1)]
		invoice = by_key(pv.build_stages(docs, today="2026-01-05"))["invoice"]
		self.assertEqual((invoice["count"], invoice["restricted"], invoice["docs"]), (1, 1, []))

	def test_doctype_fora_da_cadeia_e_rejeitado(self):
		with self.assertRaises(frappe.ValidationError):
			pv.get_purchase_steps("ToDo", "x")

	def test_cadeia_descoberta_pelos_vinculos(self):
		def vizinhos(doctype, name, edges):
			grafo = {
				("Purchase Receipt", "PR-1"): {("Purchase Order", "PO-1")},
				("Purchase Order", "PO-1"): {("Material Request", "MR-1"), ("Purchase Receipt", "PR-1")},
				("Material Request", "MR-1"): {("Purchase Order", "PO-1")},
			}
			return grafo.get((doctype, name), set())

		with patch.object(pv, "_neighbours", vizinhos), patch.object(pv, "_edges", lambda: []):
			names = pv.collect_chain("Purchase Receipt", "PR-1")
		self.assertEqual(
			names,
			{"Purchase Receipt": {"PR-1"}, "Purchase Order": {"PO-1"}, "Material Request": {"MR-1"}},
		)


class TestNotaFiscal(FrappeTestCase):
	@staticmethod
	def chave_valida(numero=123, cnpj="11222333000181"):
		base = "35" + "2610" + cnpj + "55" + "001" + f"{numero:09d}" + "1" + "12345678"
		return base + str(receipt.digito_verificador(base))

	def test_chave_valida_e_decomposta(self):
		chave = self.chave_valida()
		self.assertTrue(receipt.chave_valida(chave))
		partes = receipt.decompor_chave(chave)
		self.assertEqual(
			(int(partes["numero"]), partes["serie"], partes["cnpj"]), (123, "001", "11222333000181")
		)

	def test_chave_com_digito_errado_ou_tamanho_errado_e_invalida(self):
		chave = self.chave_valida()
		errada = chave[:-1] + str((int(chave[-1]) + 1) % 10)
		self.assertFalse(receipt.chave_valida(errada))
		self.assertFalse(receipt.chave_valida(chave[:-1]))

	def test_normalizar_chave_remove_espacos(self):
		chave = self.chave_valida()
		espacada = " ".join(chave[i : i + 4] for i in range(0, 44, 4))
		self.assertEqual(receipt.normalizar_chave(espacada), chave)

	def test_validar_preenche_numero_e_serie_pela_chave(self):
		pr = frappe._dict(custom_compras_nf_chave=self.chave_valida(456), supplier=None, grand_total=0)
		receipt.validar_nota_fiscal(pr)
		self.assertEqual((pr.custom_compras_nf_numero, pr.custom_compras_nf_serie), ("456", "1"))

	def test_validar_rejeita_chave_invalida(self):
		pr = frappe._dict(custom_compras_nf_chave="1" * 44, supplier=None, grand_total=0)
		with self.assertRaises(frappe.ValidationError):
			receipt.validar_nota_fiscal(pr)

	def test_fatura_herda_numero_e_data_do_recebimento(self):
		fatura = frappe._dict(bill_no=None, bill_date=None, items=[frappe._dict(purchase_receipt="PR-1")])
		with patch.object(frappe.db, "get_value", return_value=("987", "2026-01-02")):
			receipt.herdar_nota_fiscal(fatura)
		self.assertEqual((fatura.bill_no, fatura.bill_date), ("987", "2026-01-02"))

	def test_fatura_com_varios_recebimentos_nao_herda(self):
		itens = [frappe._dict(purchase_receipt="PR-1"), frappe._dict(purchase_receipt="PR-2")]
		fatura = frappe._dict(bill_no=None, bill_date=None, items=itens)
		receipt.herdar_nota_fiscal(fatura)
		self.assertIsNone(fatura.bill_no)
