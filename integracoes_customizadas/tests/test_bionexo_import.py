from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from integracoes_customizadas.bionexo.import_pdf import chave_nome, numero_br, parse_texto
from integracoes_customizadas.bionexo.importacao import (
	criar_fornecedores,
	rfq_por_material_request,
	vinculos_da_rfq,
)

MODULO = "integracoes_customizadas.integracoes_customizadas.doctype.importacao_bionexo.importacao_bionexo"
PARSER = f"{MODULO}.parse_relatorio"
CLASSE = f"{MODULO}.ImportacaoBionexo"


def cnpj(base12: str) -> str:
	pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
	numeros = [int(c) for c in base12]
	for pesos_dv in (pesos, [6, *pesos]):
		resto = sum(n * p for n, p in zip(numeros, pesos_dv, strict=False)) % 11
		numeros.append(0 if resto < 2 else 11 - resto)
	d = "".join(map(str, numeros))
	return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


CNPJ_ALFA, CNPJ_BETA, CNPJ_GAMA = cnpj("910000010001"), cnpj("910000020001"), cnpj("910000030001")


def resposta(nome_linhas, qty, rate, total, status, extra=""):
	cabecalho = "Fornecedor Informações do produto Qntd. Preço unit.(R$) Total(R$) Status"
	return f"""{cabecalho}
{nome_linhas}
Marca: MARCA &#43; GENERICA
Embalagem: 100 - CX
{qty} R$ {rate} R$ {total} {status}
{extra}Observação
do
fornecedor:
Validade: 30/06/2028
Justificativa de escolha:-"""


def relatorio(rfq, codigos):
	a, b, c = codigos
	confirmado_por = "Confirmado por:Comprador no dia 20/10/2026 às 16h28m\n"
	alfa_a = resposta(
		"Alfa Distribuidora\nLtda\nItem: -", 10, "2,5000", "25,00", "Confirmado", confirmado_por
	)
	gama_a = resposta("Gama Comercio de Produtos Medicos Ltda Item: -", 10, "2,6000", "26,00", "Para análise")
	beta_b = resposta(
		"Beta Hospitalar Ltda\nItem: B-OFERTADO", "1.000", "1,1000", "1.100,00", "Confirmado", confirmado_por
	)
	beta_c = resposta(
		"Beta Hospitalar Ltda\nItem: C-OFERTADO",
		2,
		"1.132,0000",
		"2.264,00",
		"Confirmado",
		"Confirmado por:Comprador no dia 21/10/2026 às 10h18m\n",
	)
	gama_c = resposta(
		"Gama Comercio de Produtos\nMedicos Ltda\nItem: -", 2, "1.200,0000", "2.400,00", "Para análise"
	)
	return f"""Relatório geral de PDC
Título: TESTE_IMPORTACAO
ID: 999000111 ID do upload: 999000222 Tipo de cotação: Cotação Normal Criado por: Comprador Teste
Data de criação
20/10/2026 às 15h21min
Vencimento
20/10/2026 às 16h15min
Forma de pagamento
30 ddl
Observações
{rfq}
Termos e condições
---
1 Código
{a}
Nome do item
ITEM A TESTE | Unidade
Embalagem
Unidade
Qntd. solicitada
10
Últimas compras:
Data:25.09.2026
Fornecedor:QUALQUER UM
Qntd:1 Preço unit.:R$1,0000
{alfa_a}
{gama_a}
2 Código
{b}
Nome do item
ITEM B TESTE | Ampola
Embalagem
Ampola
Qntd. solicitada
1.000
{beta_b}
3 Código
{c}
Nome do item
ITEM C TESTE | Unidade
Embalagem
Unidade
Qntd. solicitada
2
{beta_c}
{gama_c}
Fornecedores participantes desta cotação
Fornecedor e CNPJ Contato Envio Válido até Pagamento Faturamento mínimo (R$)
Alfa Distribuidora Ltda
{CNPJ_ALFA}
Usuario Ws
(11) 3333-4444
vendas@alfa.example
Frete: CIF
Entrega: 2 dias
23/10/2026 30 ddl 500,00
Beta Hospitalar
Ltda
{CNPJ_BETA}
Usuario Ws
vendas@beta.example
Frete: CIF
Entrega: 1 dias
25/10/2026 25 dia do mês subsequente 1.000,00
Gama Comercio de
Produtos Medicos Ltda
{CNPJ_GAMA}
Usuario Ws
(00) 00000-0000
vendas@gama.example
Frete: CIF
Entrega: 3 dias
23/10/2026 A COMBINAR 350,00
Resumo dos valores por fornecedor
Itens confirmados
Fornecedor Número de itens Total (R$)
Alfa Distribuidora Ltda 1 25,00
Beta Hospitalar Ltda 2 3.364,00
Total de fornecedores confirmados
2
"""


class TestParserBionexo(FrappeTestCase):
	def test_le_cabecalho_itens_respostas_e_participantes(self):
		dados = parse_texto(relatorio("COMPRA-PDC-2026-00001", ("A1", "B2", "C3")))

		self.assertEqual(dados["id_cotacao"], "999000111")
		self.assertEqual(dados["observacoes"], "COMPRA-PDC-2026-00001")
		self.assertEqual(dados["data_criacao"], "2026-10-20")
		self.assertEqual([i["codigo"] for i in dados["itens"]], ["A1", "B2", "C3"])
		self.assertEqual(dados["itens"][1]["qtd_solicitada"], 1000)
		self.assertEqual(dados["itens"][1]["unidade"], "Ampola")
		self.assertEqual([len(i["respostas"]) for i in dados["itens"]], [2, 1, 2])
		self.assertEqual(len(dados["participantes"]), 3)
		self.assertEqual(dados["participantes"][1]["validade"], "2026-10-25")
		self.assertEqual(dados["participantes"][1]["pagamento"], "25 dia do mês subsequente")
		self.assertEqual(
			dados["confirmados"][1], {"nome": "Beta Hospitalar Ltda", "itens": 2, "total": 3364.0}
		)

	def test_resposta_resolve_cnpj_pelo_nome_mesmo_com_nome_quebrado_ou_colado(self):
		itens = parse_texto(relatorio("X", ("A1", "B2", "C3")))["itens"]
		alfa, gama = itens[0]["respostas"]
		self.assertEqual(alfa["fornecedor"], "Alfa Distribuidora Ltda")
		self.assertEqual(alfa["cnpj"], CNPJ_ALFA)
		self.assertEqual(alfa["status"], "Confirmado")
		self.assertEqual(alfa["marca"], "MARCA + GENERICA")
		self.assertEqual(alfa["observacao"], "Validade: 30/06/2028")
		self.assertTrue(alfa["confirmado_por"].startswith("Comprador"))
		self.assertEqual(alfa["data_confirmacao"], "2026-10-20 16:28:00")
		self.assertIsNone(gama["data_confirmacao"])
		self.assertEqual(gama["cnpj"], CNPJ_GAMA)
		c_gama = itens[2]["respostas"][1]
		self.assertEqual((c_gama["qty"], c_gama["rate"], c_gama["amount"]), (2, 1200.0, 2400.0))

	def test_item_sem_resposta_de_fornecedor_nao_quebra_a_leitura(self):
		def sem_resposta(seq, codigo):
			return (
				f"{seq} Código\n{codigo}\nNome doitem\nITEM SEM COTACAO | Unidade\nEmbalagem\nUnidade\n"
				"Qntd. solicitada\n3\nÚltimas compras:\nData:25.09.2026\nFornecedor:QUALQUER UM\n"
				"Qntd:1 Preço unit.:R$1,0000\n"
			)

		texto = relatorio("X", ("A1", "B2", "C3"))
		texto = texto.replace("2 Código\nB2", sem_resposta(2, "S1") + "3 Código\nB2", 1)
		texto = texto.replace("3 Código\nC3", "4 Código\nC3", 1)
		texto = texto.replace(
			"Fornecedores participantes desta cotação",
			sem_resposta(5, "S2") + "Fornecedores participantes desta cotação",
			1,
		)
		itens = parse_texto(texto)["itens"]

		self.assertEqual([i["codigo"] for i in itens], ["A1", "S1", "B2", "C3", "S2"])
		self.assertEqual([len(i["respostas"]) for i in itens], [2, 0, 1, 2, 0])

	def test_numeros_e_nomes(self):
		self.assertEqual(numero_br("1.132,0000"), 1132.0)
		self.assertEqual(numero_br("0,8208"), 0.8208)
		self.assertEqual(numero_br("1.000"), 1000)
		self.assertEqual(chave_nome("Ello DistribuicaoLtda"), chave_nome("Ello Distribuição Ltda"))

	def test_rejeita_arquivo_que_nao_e_relatorio(self):
		with self.assertRaises(ValueError):
			parse_texto("Nota fiscal qualquer")


class TestImportacaoBionexo(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		warehouse = frappe.get_all(
			"Warehouse", filters={"is_group": 0, "disabled": 0}, fields=["name", "company"], limit=1
		)[0]
		cls.company, cls.warehouse = warehouse.company, warehouse.name
		grupo = frappe.db.get_value("Item Group", {"is_group": 0})
		cls.itens = []
		for sufixo in ("A", "B", "C"):
			codigo = f"_TST-BNX-{sufixo}"
			if not frappe.db.exists("Item", codigo):
				frappe.get_doc(
					{
						"doctype": "Item",
						"item_code": codigo,
						"item_name": codigo,
						"item_group": grupo,
						"stock_uom": "Nos"
						if frappe.db.exists("UOM", "Nos")
						else frappe.db.get_value("UOM", {}),
						"is_stock_item": 0,
					}
				).insert()
			cls.itens.append(codigo)
		frappe.db.set_value("Item", "_TST-BNX-B", "custom_código_bionexo", "BNX-COD-B")

		for nome, numero in (("_TST ALFA DISTRIBUIDORA", CNPJ_ALFA), ("_TST BETA HOSPITALAR", CNPJ_BETA)):
			if not frappe.db.exists("Supplier", nome):
				frappe.get_doc({"doctype": "Supplier", "supplier_name": nome, "tax_id": numero}).insert()

		mr = frappe.get_doc(
			{
				"doctype": "Material Request",
				"material_request_type": "Purchase",
				"company": cls.company,
				"schedule_date": add_days(nowdate(), 5),
				"items": [
					{
						"item_code": codigo,
						"qty": qty,
						"schedule_date": add_days(nowdate(), 5),
						"warehouse": cls.warehouse,
					}
					for codigo, qty in zip(cls.itens, (10, 1000, 2), strict=True)
				],
			}
		)
		mr.flags.ignore_mandatory = True
		mr.insert()
		mr.submit()
		cls.mr = mr.name

		from erpnext.stock.doctype.material_request.material_request import make_request_for_quotation

		rfq = make_request_for_quotation(mr.name)
		rfq.message_for_supplier = "Teste"
		rfq.flags.ignore_mandatory = True
		rfq.insert()
		rfq.submit()
		cls.rfq = rfq.name

	def setUp(self):
		frappe.db.savepoint("teste_bionexo")

	def tearDown(self):
		frappe.db.rollback(save_point="teste_bionexo")

	def new_import(self, observacao=None, codigos=("_TST-BNX-A", "BNX-COD-B", "DESCONHECIDO"), **campos):
		dados = parse_texto(relatorio(observacao or self.rfq, codigos))
		with patch(PARSER, return_value=dados), patch(f"{CLASSE}.conteudo_pdf", return_value=b""):
			return frappe.get_doc(
				{"doctype": "Importacao Bionexo", "arquivo_pdf": "bionexo-teste.pdf", **campos}
			).insert()

	def new_material_request(self):
		mr = frappe.get_doc(
			{
				"doctype": "Material Request",
				"material_request_type": "Purchase",
				"company": self.company,
				"schedule_date": add_days(nowdate(), 5),
				"items": [
					{
						"item_code": codigo,
						"qty": qty,
						"schedule_date": add_days(nowdate(), 5),
						"warehouse": self.warehouse,
					}
					for codigo, qty in zip(self.itens, (10, 1000, 2), strict=True)
				],
			}
		)
		mr.flags.ignore_mandatory = True
		mr.insert()
		mr.submit()
		return mr.name

	def test_rfq_cited_from_another_bionexo_quotation_is_not_linked(self):
		# Quotation copied in Bionexo: the title/remarks cite the RFQ of the previous round, already imported
		# with another Bionexo ID.
		anterior = self.new_import()
		self.assertEqual(anterior.request_for_quotation, self.rfq)
		frappe.db.set_value("Importacao Bionexo", anterior.name, "id_cotacao_bionexo", "123456")
		doc = self.new_import()
		self.assertFalse(doc.request_for_quotation)
		self.assertFalse(doc.material_request)

	def test_cited_rfq_without_report_items_is_not_linked(self):
		doc = self.new_import(codigos=("DESCONHECIDO-1", "DESCONHECIDO-2", "DESCONHECIDO-3"))
		self.assertFalse(doc.request_for_quotation)

	def test_chosen_reference_is_not_replaced_by_the_pdf(self):
		mr = self.new_material_request()
		# The report cites the RFQ of another Purchase Request: the chosen Purchase Request prevails (the RFQ will be generated).
		doc = self.new_import(material_request=mr)
		self.assertEqual((doc.material_request, doc.request_for_quotation), (mr, None))

		dados = parse_texto(relatorio(self.rfq, ("_TST-BNX-A", "_TST-BNX-B", "_TST-BNX-C")))
		with patch(PARSER, return_value=dados), patch(f"{CLASSE}.conteudo_pdf", return_value=b""):
			doc.reanalisar()
		self.assertEqual((doc.material_request, doc.request_for_quotation), (mr, None))

	def test_rfq_cleared_by_the_user_does_not_return_on_save(self):
		doc = self.new_import()
		self.assertEqual(doc.request_for_quotation, self.rfq)
		doc.request_for_quotation = None
		doc.save()
		self.assertFalse(doc.request_for_quotation)
		self.assertEqual(doc.material_request, self.mr)

	def test_purchase_order_cancels_and_deletes_with_a_submitted_import(self):
		self.assertIn("Importacao Bionexo", frappe.get_hooks("auto_cancel_exempted_doctypes"))
		doc = self.new_import(codigos=("_TST-BNX-A", "_TST-BNX-B", "_TST-BNX-C"))
		doc.gerar_demais_fornecedores = 0
		doc.save()
		doc.submit()
		ordens = {c.supplier: c.purchase_order for c in doc.cotacoes if c.purchase_order}

		beta = frappe.get_doc("Purchase Order", ordens["_TST BETA HOSPITALAR"])
		beta.submit()
		frappe.db.savepoint("cancelar_importacao")
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc("Importacao Bionexo", doc.name).cancel()
		frappe.db.rollback(save_point="cancelar_importacao")
		# Before: LinkExistsError ("is linked with Importacao Bionexo"), with no way out. Only the import is
		# ignored: the list of links that block stays the same without it.
		from frappe.model.delete_doc import get_linked_docs

		from integracoes_customizadas.bionexo.importacao import release_cancellation

		beta.reload()
		sem_hook = {d["reference_doctype"] for d in get_linked_docs(beta, method="Cancel")}
		self.assertIn("Importacao Bionexo", sem_hook)
		release_cancellation(beta)
		com_hook = {d["reference_doctype"] for d in get_linked_docs(beta, method="Cancel")}
		self.assertEqual(com_hook, sem_hook - {"Importacao Bionexo"})
		beta.reload()
		beta.cancel()
		self.assertEqual(beta.docstatus, 2)

		frappe.delete_doc("Purchase Order", ordens["_TST ALFA DISTRIBUIDORA"])
		self.assertTrue(
			frappe.db.exists(
				"Comment",
				{
					"reference_doctype": "Importacao Bionexo",
					"reference_name": doc.name,
					"content": ["like", f"%{ordens['_TST ALFA DISTRIBUIDORA']}%"],
				},
			)
		)
		self.assertFalse(
			frappe.db.exists(
				"Importacao Bionexo Cotacao", {"purchase_order": ordens["_TST ALFA DISTRIBUIDORA"]}
			)
		)

		doc = frappe.get_doc("Importacao Bionexo", doc.name)
		doc.cancel()
		self.assertEqual(doc.status, "Cancelado")
		orcamentos = {c.supplier_quotation for c in doc.cotacoes if c.supplier_quotation}
		self.assertEqual({frappe.db.get_value("Supplier Quotation", n, "docstatus") for n in orcamentos}, {2})

	def test_identifica_rfq_itens_e_fornecedores_pelo_relatorio(self):
		doc = self.new_import()

		self.assertEqual(doc.request_for_quotation, self.rfq)
		self.assertEqual(doc.material_request, self.mr)
		self.assertEqual(doc.company, self.company)
		self.assertEqual(
			[(i.item_code, i.situacao) for i in doc.itens],
			[("_TST-BNX-A", "Identificado"), ("_TST-BNX-B", "Identificado"), (None, "Não identificado")],
		)
		situacoes = {f.cnpj: (f.supplier, f.situacao) for f in doc.fornecedores}
		self.assertEqual(situacoes[CNPJ_ALFA], ("_TST ALFA DISTRIBUIDORA", "Encontrado"))
		self.assertEqual(situacoes[CNPJ_GAMA], (None, "Não cadastrado"))
		self.assertEqual(doc.status, "Pendências")
		with self.assertRaises(frappe.ValidationError):
			doc.submit()

	def test_filtro_de_rfq_pela_solicitacao_e_vinculos(self):
		encontrados = rfq_por_material_request(
			"Request for Quotation", "", "name", 0, 20, {"material_request": self.mr}
		)
		self.assertEqual([r[0] for r in encontrados], [self.rfq])
		vinculos = vinculos_da_rfq(self.rfq)
		self.assertEqual(vinculos["material_requests"], [self.mr])
		self.assertEqual(vinculos["item_codes"], sorted(self.itens))

	def test_rfq_escolhida_manualmente_preenche_a_solicitacao(self):
		doc = self.new_import(observacao="SEM REFERENCIA")
		self.assertFalse(doc.request_for_quotation)
		doc.request_for_quotation = self.rfq
		doc.save()
		self.assertEqual(doc.material_request, self.mr)

	def test_conclusao_gera_orcamentos_submetidos_e_ordens_em_rascunho(self):
		doc = self.new_import()
		with patch("busca_cnpj.api.lookup_cnpj", side_effect=frappe.ValidationError("offline")):
			resultado = criar_fornecedores(doc.name)
		self.assertEqual(len(resultado["criados"]), 1)
		self.assertEqual(frappe.db.get_value("Supplier", resultado["criados"][0], "tax_id"), CNPJ_GAMA)

		doc.reload()
		doc.itens[2].item_code = "_TST-BNX-C"
		doc.save()
		self.assertEqual(doc.status, "Pronto")
		doc.submit()

		orcamentos = {c.supplier_quotation for c in doc.cotacoes}
		self.assertEqual(len(orcamentos), 3)
		for nome in orcamentos:
			orcamento = frappe.get_doc("Supplier Quotation", nome)
			self.assertEqual(orcamento.docstatus, 1)
			self.assertTrue(all(i.request_for_quotation == self.rfq for i in orcamento.items))

		ordens = {c.supplier: c.purchase_order for c in doc.cotacoes if c.purchase_order}
		self.assertEqual(set(ordens), {"_TST ALFA DISTRIBUIDORA", "_TST BETA HOSPITALAR"})
		beta = frappe.get_doc("Purchase Order", ordens["_TST BETA HOSPITALAR"])
		self.assertEqual(beta.docstatus, 0)
		# Data da OC = confirmação mais recente no Bionexo entre os itens do fornecedor (B 20/10, C 21/10)
		self.assertEqual(str(beta.transaction_date), "2026-10-21")
		self.assertTrue(all(i.schedule_date >= beta.transaction_date for i in beta.items))
		self.assertEqual(
			sorted((i.item_code, i.qty, i.rate, i.material_request) for i in beta.items),
			[("_TST-BNX-B", 1000, 1.1, self.mr), ("_TST-BNX-C", 2, 1132.0, self.mr)],
		)
		self.assertEqual(
			frappe.db.get_value("Request for Quotation", self.rfq, "custom_id_bionexo"), "999000111"
		)

		with self.assertRaises(frappe.ValidationError):
			self.new_import()

		doc.cancel()
		self.assertFalse(frappe.db.exists("Purchase Order", beta.name))
		self.assertEqual({frappe.db.get_value("Supplier Quotation", n, "docstatus") for n in orcamentos}, {2})

	def test_sem_demais_fornecedores_gera_orcamento_so_dos_vencedores_e_itens_confirmados(self):
		doc = self.new_import(codigos=("_TST-BNX-A", "_TST-BNX-B", "_TST-BNX-C"))
		doc.gerar_demais_fornecedores = 0
		doc.save()
		# Gama (sem cadastro e sem item confirmado) não bloqueia: não vai gerar orçamento
		self.assertEqual(doc.status, "Pronto")
		doc.submit()

		fornecedores = {c.supplier for c in doc.cotacoes if c.supplier_quotation}
		self.assertEqual(fornecedores, {"_TST ALFA DISTRIBUIDORA", "_TST BETA HOSPITALAR"})
		itens = {
			c.supplier: sorted(
				i.item_code for i in frappe.get_doc("Supplier Quotation", c.supplier_quotation).items
			)
			for c in doc.cotacoes
			if c.supplier_quotation
		}
		self.assertEqual(itens["_TST ALFA DISTRIBUIDORA"], ["_TST-BNX-A"])
		self.assertEqual(itens["_TST BETA HOSPITALAR"], ["_TST-BNX-B", "_TST-BNX-C"])

	def test_gera_pedido_de_cotacao_quando_a_solicitacao_nao_tem(self):
		mr = frappe._dict(name=self.new_material_request())

		doc = self.new_import(observacao=mr.name, codigos=("_TST-BNX-A", "_TST-BNX-B", "_TST-BNX-C"))
		self.assertFalse(doc.request_for_quotation)
		self.assertEqual(doc.material_request, mr.name)
		self.assertEqual(doc.company, self.company)
		self.assertEqual({i.situacao for i in doc.itens}, {"Identificado"})
		doc.gerar_demais_fornecedores = 0
		doc.save()
		doc.submit()

		self.assertTrue(doc.rfq_gerada)
		rfq = frappe.get_doc("Request for Quotation", doc.request_for_quotation)
		self.assertEqual((rfq.docstatus, rfq.custom_id_bionexo), (1, "999000111"))
		self.assertEqual(sorted(i.item_code for i in rfq.items), sorted(self.itens))
		self.assertEqual(
			sorted(s.supplier for s in rfq.suppliers),
			["_TST ALFA DISTRIBUIDORA", "_TST BETA HOSPITALAR"],
		)
		self.assertTrue(all(c.rfq_item for c in doc.cotacoes))

		doc.cancel()
		self.assertEqual(frappe.db.get_value("Request for Quotation", rfq.name, "docstatus"), 2)


class TestImportLinks(FrappeTestCase):
	"""Cancel/delete hooks, without a database (style of the doc_events tests of clm)."""

	def test_cancellation_keeps_the_ignored_doctypes_of_the_controller_and_only_adds_the_import(self):
		from integracoes_customizadas.bionexo.importacao import release_cancellation

		doc = frappe._dict(
			doctype="Purchase Order", ignore_linked_doctypes=("GL Entry", "Payment Ledger Entry")
		)
		release_cancellation(doc)
		release_cancellation(doc)  # idempotent
		self.assertEqual(
			doc.ignore_linked_doctypes, ("GL Entry", "Payment Ledger Entry", "Importacao Bionexo")
		)

	def test_deleting_a_doctype_without_a_link_writes_nothing(self):
		from integracoes_customizadas.bionexo.importacao import unlink_on_delete

		with patch("frappe.db.set_value") as set_value, patch("frappe.get_all") as get_all:
			unlink_on_delete(frappe._dict(doctype="Purchase Invoice", name="X"))
		set_value.assert_not_called()
		get_all.assert_not_called()
