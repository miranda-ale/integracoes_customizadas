import json
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from integracoes_customizadas.juridico import datajud
from integracoes_customizadas.juridico.doctype.processo_judicial.processo_judicial import _datajud_datetime


NUMERO = "00008323520184013202"
IDENTIFICADOR = f"TRF1_436_JE_16403_{NUMERO}"


def _fonte(identificador=IDENTIFICADOR, numero=NUMERO):
	return {
		"id": identificador,
		"numeroProcesso": numero,
		"tribunal": "TRF1",
		"grau": "JE",
		"nivelSigilo": 0,
		"classe": {"codigo": 436, "nome": "Procedimento do Juizado"},
		"sistema": {"codigo": 1, "nome": "PJe"},
		"formato": {"codigo": 1, "nome": "Eletrônico"},
		"orgaoJulgador": {"codigo": 16403, "nome": "Vara", "codigoMunicipioIBGE": 5128},
		"dataAjuizamento": "2018-10-29T00:00:00.000Z",
		"dataHoraUltimaAtualizacao": "2023-07-21T19:10:08.483Z",
		"@timestamp": "2023-08-14T11:50:51.994Z",
		"assuntos": [{"codigo": 6177, "nome": "Concessão"}],
		"movimentos": [{
			"codigo": 26,
			"nome": "Distribuição",
			"dataHora": "2018-10-30T14:06:24.000Z",
			"orgaoJulgador": {"codigoOrgao": 16403, "nomeOrgao": "Vara"},
			"complementosTabelados": [{"codigo": 2, "valor": 1, "nome": "Competência"}],
		}],
	}


class TestProcessoJudicialDataJud(FrappeTestCase):
	def test_endpoint_aliases_and_pagination_filter_exact_number(self):
		self.assertIn("tre-ac", datajud.TRIBUNAIS)
		self.assertEqual(datajud._alias_do_tribunal("TRE-AC"), "tre-ac")
		with patch.object(datajud, "PAGE_SIZE", 2), patch.object(datajud, "_post") as post:
			post.side_effect = [
				{"hits": {"hits": [
					{"_id": "um", "_source": _fonte("um"), "sort": [1]},
					{"_id": "ignorar", "_source": {**_fonte("ignorar"), "numeroProcesso": "0" * 20}, "sort": [2]},
				]}},
				{"hits": {"hits": [{"_id": "dois", "_source": _fonte("dois"), "sort": [3]}]}},
			]
			resultados = datajud.consultar_numero(NUMERO, "trf1", "chave")
		self.assertEqual([id for id, _ in resultados], ["um", "dois"])
		self.assertEqual(post.call_args_list[1].args[1]["search_after"], [2])

	def test_no_hits_and_incomplete_response(self):
		with patch.object(datajud, "_post", return_value={"hits": {"hits": []}}):
			self.assertEqual(datajud.consultar_numero(NUMERO, "trf1", "chave"), [])
		with patch.object(datajud, "_post", return_value={"timed_out": True, "hits": {"hits": []}}):
			with self.assertRaises(datajud.DataJudError):
				datajud.consultar_numero(NUMERO, "trf1", "chave")

	def test_http_errors_and_retry(self):
		with patch.object(datajud.requests, "post") as post, patch.object(datajud.time, "sleep"):
			post.side_effect = [Mock(status_code=429), Mock(status_code=200, json=lambda: {"hits": {"hits": []}})]
			self.assertIn("hits", datajud._post("trf1", {}, "chave"))
			self.assertEqual(post.call_count, 2)
			post.side_effect = None
			post.return_value = Mock(status_code=401)
			with self.assertRaises(datajud.DataJudError):
				datajud._post("trf1", {}, "chave")
			post.side_effect = [
				Mock(status_code=200, json=lambda: {"timed_out": False, "_shards": {"failed": 1}}),
				Mock(status_code=200, json=lambda: {"timed_out": False, "_shards": {"failed": 0}}),
			]
			self.assertEqual(datajud._post("trf1", {}, "chave")["_shards"]["failed"], 0)

	def test_mapping_and_repeated_update(self):
		identificador = f"TRF1_436_JE_16403_{NUMERO}"
		fonte = _fonte(identificador)
		datajud._espelhar_ocorrencia(identificador, fonte)
		doc = frappe.get_doc("Processo Judicial", identificador)
		self.assertEqual(doc.numero_processo, "0000832-35.2018.4.01.3202")
		self.assertEqual(doc.classe_codigo, 436)
		self.assertEqual(doc.data_ajuizamento_original, fonte["dataAjuizamento"])
		self.assertEqual(len(doc.assuntos), 1)
		self.assertEqual(doc.assuntos[0].assunto, "6177")
		self.assertEqual(frappe.db.get_value("Assunto Judicial", "6177", "nome"), "Concessão")
		self.assertEqual(len(doc.movimentos), 1)
		self.assertEqual(doc.movimentos[0].orgao_julgador_codigo, "16403")
		self.assertEqual(json.loads(doc.movimentos[0].complementos_tabelados)[0]["codigo"], 2)
		fonte["classe"]["nome"] = "Classe atualizada"
		fonte["movimentos"] = []
		datajud._espelhar_ocorrencia(identificador, fonte)
		doc.reload()
		self.assertEqual(doc.classe_nome, "Classe atualizada")
		self.assertFalse(doc.movimentos)
		self.assertEqual(frappe.db.count("Processo Judicial", {"datajud_id": identificador}), 1)

	def test_consulta_prepara_rascunhos_sem_gravar_processos(self):
		fonte_um = _fonte("primeira-ocorrencia")
		fonte_um["assuntos"] = [
			{"codigo": 99393939, "nome": "Assunto novo um"},
			{"codigo": 99393938, "nome": "Assunto novo dois"},
		]
		fonte_dois = _fonte("segunda-ocorrencia")
		with patch.object(datajud, "_post", return_value={"hits": {"hits": [
			{"_id": "primeira-ocorrencia", "_source": fonte_um},
			{"_id": "segunda-ocorrencia", "_source": fonte_dois},
		]}}), patch.object(datajud, "_chave_publica", return_value="chave"):
			resultados = datajud.acompanhar_processo(NUMERO, "trf1")
		self.assertEqual([item["doc"]["datajud_id"] for item in resultados], ["primeira-ocorrencia", "segunda-ocorrencia"])
		self.assertFalse(frappe.db.exists("Processo Judicial", {"datajud_id": "primeira-ocorrencia"}))
		self.assertFalse(frappe.db.exists("Assunto Judicial", "99393939"))
		self.assertFalse(frappe.db.exists("Assunto Judicial", "99393938"))
		doc = frappe.get_doc(json.loads(frappe.as_json(resultados[0]["doc"])))
		doc.numero_processo = "alterado-no-cliente"
		doc.risco = "Baixo"
		doc.save()
		self.assertEqual(doc.datajud_id, "primeira-ocorrencia")
		self.assertEqual(doc.numero_processo, datajud._numero_cnj_formatado(NUMERO))
		self.assertEqual(doc.risco, "Baixo")
		self.assertTrue(frappe.db.exists("Assunto Judicial", "99393939"))
		self.assertTrue(frappe.db.exists("Assunto Judicial", "99393938"))
		with patch.object(datajud, "_post", return_value={"hits": {"hits": [
			{"_id": "primeira-ocorrencia", "_source": fonte_um},
		]}}), patch.object(datajud, "_chave_publica", return_value="chave"):
			self.assertEqual(datajud.acompanhar_processo(NUMERO, "trf1"), [
				{"name": "primeira-ocorrencia", "existente": True}
			])
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(resultados[1]["doc"] | {"consulta_token": None}).save()
		with patch.object(datajud, "_post", return_value={"hits": {"hits": []}}), patch.object(
			datajud, "_chave_publica", return_value="chave"
		):
			self.assertEqual(datajud.acompanhar_processo("1" * 20, "trf1"), [])
		self.assertEqual(frappe.db.count("Processo Judicial", {"numero_processo": datajud._numero_cnj_formatado("1" * 20)}), 0)

	def test_dates_accept_iso_and_legacy_ajuizamento(self):
		self.assertIsNotNone(_datajud_datetime("2018-10-29T00:00:00.000Z", "dataAjuizamento", ajuizamento=True))
		self.assertEqual(
			_datajud_datetime("20181029000000", "dataAjuizamento", ajuizamento=True).year, 2018
		)

	def test_acao_exige_funcao_autorizada(self):
		usuario_original = frappe.session.user
		try:
			frappe.set_user("juridico-datajud@example.com")
			with patch("frappe.get_roles", return_value=["Usuário Jurídico"]):
				self.assertIn("tre-ac", [t["value"] for t in datajud.listar_tribunais()])
			with patch("frappe.get_roles", return_value=["System Manager"]):
				self.assertIn("tre-ac", [t["value"] for t in datajud.listar_tribunais()])
			with patch("frappe.get_roles", return_value=[]):
				with self.assertRaises(frappe.PermissionError):
					datajud.listar_tribunais()
		finally:
			frappe.set_user(usuario_original)

	def test_permissions_and_manual_write_blocked(self):
		meta = frappe.get_meta("Processo Judicial")
		self.assertTrue(meta.get_field("nome_parte").in_list_view)
		self.assertFalse(meta.get_field("situacao_cadastro").in_list_view)
		self.assertEqual({(p.role, p.read, p.write, p.create) for p in meta.permissions}, {
			("Usuário Jurídico", 1, 1, 1),
			("System Manager", 1, 1, 1),
		})
		self.assertEqual(
			[(p.role, p.read, p.write) for p in frappe.get_meta("Configurações DataJud").permissions],
			[("System Manager", 1, 1)],
		)
		self.assertTrue(frappe.db.exists("Role", "Usuário Jurídico"))
		self.assertTrue(frappe.has_permission("Configurações DataJud", "read", user="Administrator"))
		with patch("frappe.get_roles", return_value=["System Manager"]):
			self.assertTrue(frappe.has_permission(
				"Configurações DataJud", "read", user="gestor-datajud@example.com"
			))
			self.assertTrue(frappe.has_permission(
				"Configurações DataJud", "write", user="gestor-datajud@example.com"
			))
		with patch("frappe.get_roles", return_value=["Usuário Jurídico"]):
			self.assertFalse(frappe.has_permission(
				"Configurações DataJud", "read", user="juridico-datajud@example.com"
			))
		with patch("frappe.get_roles", return_value=["Usuário Jurídico"]):
			self.assertTrue(frappe.has_permission(
				"Processo Judicial", "read", user="juridico-datajud@example.com"
			))
			self.assertTrue(frappe.has_permission(
				"Processo Judicial", "write", user="juridico-datajud@example.com"
			))
		with patch("frappe.get_roles", return_value=["System Manager"]):
			self.assertTrue(frappe.has_permission(
				"Processo Judicial", "read", user="gestor-datajud@example.com"
			))
			self.assertTrue(frappe.has_permission(
				"Processo Judicial", "write", user="gestor-datajud@example.com"
			))
		doc = frappe.new_doc("Processo Judicial")
		doc.datajud_id = IDENTIFICADOR
		with self.assertRaises(frappe.ValidationError):
			doc.validate()

	def test_cadastro_preservado_na_atualizacao_e_campos_datajud_protegidos(self):
		datajud._espelhar_ocorrencia(IDENTIFICADOR, _fonte())
		doc = frappe.get_doc("Processo Judicial", IDENTIFICADOR)
		self.assertEqual(doc.situacao_cadastro, "Rascunho")
		doc.empresa = frappe.get_all("Company", pluck="name", limit=1)[0]
		doc.valor_causa = 1500
		doc.valor_condenacao = 200
		doc.risco = "Médio"
		doc.fase_processo = "Instrutória"
		doc.save()
		doc.reload()
		self.assertEqual(doc.valor_causa, 1500)
		self.assertEqual((doc.risco, doc.fase_processo), ("Médio", "Instrutória"))
		with self.assertRaises(frappe.ValidationError):
			doc.situacao_cadastro = "Cadastrado"
			doc.save()
		doc.reload()
		doc.numero_processo = "1" * 20
		with self.assertRaises(frappe.ValidationError):
			doc.save()
		datajud._espelhar_ocorrencia(IDENTIFICADOR, _fonte())
		doc.reload()
		self.assertEqual(doc.empresa, frappe.get_all("Company", pluck="name", limit=1)[0])
		self.assertEqual(doc.valor_causa, 1500)
		self.assertEqual((doc.risco, doc.fase_processo), ("Médio", "Instrutória"))

	def test_salvar_formulario_com_datas_serializadas_preserva_dados_datajud(self):
		datajud._espelhar_ocorrencia(IDENTIFICADOR, _fonte())
		doc = frappe.get_doc("Processo Judicial", IDENTIFICADOR)
		doc = frappe.get_doc(json.loads(frappe.as_json(doc.as_dict())))
		doc.risco = "Baixo"
		doc.save()
		doc.reload()
		self.assertEqual(doc.risco, "Baixo")
		self.assertEqual(len(doc.movimentos), 1)
		doc.data_ajuizamento = "2099-01-01 00:00:00"
		with self.assertRaises(frappe.ValidationError):
			doc.save()

	def test_assuntos_na_primeira_aba_com_multiselect_e_migracao(self):
		from integracoes_customizadas.patches.backfill_assuntos_judiciais import execute

		meta = frappe.get_meta("Processo Judicial")
		self.assertEqual(meta.get_field("assuntos").fieldtype, "Table MultiSelect")
		ordem = [field.fieldname for field in meta.fields]
		self.assertLess(ordem.index("assuntos"), ordem.index("aba_movimentos"))
		self.assertEqual(frappe.get_meta("Processo Judicial Assunto").get_field("assunto").options, "Assunto Judicial")
		datajud._espelhar_ocorrencia(IDENTIFICADOR, _fonte())
		linha = frappe.get_doc("Processo Judicial", IDENTIFICADOR).assuntos[0]
		frappe.db.set_value("Processo Judicial Assunto", linha.name, "assunto", None)
		execute()
		self.assertEqual(frappe.db.get_value("Processo Judicial Assunto", linha.name, "assunto"), "6177")

	def test_movimentos_mais_recentes_primeiro_e_campos_ocultos(self):
		fonte = _fonte()
		fonte["movimentos"].append({
			"codigo": 27, "nome": "Decisão", "dataHora": "2024-01-30T14:06:24.000Z"
		})
		datajud._espelhar_ocorrencia(IDENTIFICADOR, fonte)
		doc = frappe.get_doc("Processo Judicial", IDENTIFICADOR)
		self.assertEqual([m.codigo for m in doc.movimentos], [27, 26])
		meta = frappe.get_meta("Processo Judicial")
		self.assertTrue(meta.get_field("data_ajuizamento_original").hidden)
		self.assertTrue(meta.get_field("classe_codigo").hidden)
		movimento_meta = frappe.get_meta("Processo Judicial Movimento")
		self.assertTrue(movimento_meta.get_field("data_hora_original").hidden)
		self.assertTrue(movimento_meta.get_field("data_hora").in_list_view)

	def test_system_manager_ve_indicadores_e_dashboard_juridico(self):
		from frappe.desk.desktop import Workspace
		from frappe.desk.doctype.dashboard.dashboard import get_permitted_cards, get_permitted_charts

		usuario = "datajud-workspace-test@example.com"
		frappe.get_doc({
			"doctype": "User",
			"email": usuario,
			"first_name": "Gestor DataJud",
			"send_welcome_email": 0,
			"user_type": "System User",
		}).insert(ignore_permissions=True)
		frappe.get_doc("User", usuario).add_roles("System Manager")
		usuario_original = frappe.session.user
		try:
			frappe.set_user(usuario)
			workspace = Workspace({"name": "Jurídico"})
			blocos = frappe.parse_json(workspace.doc.content)
			self.assertEqual([block["type"] for block in blocos],
				["number_card"] * 3 + ["shortcut"] * 4 + ["card", "card", "custom_block", "card"])
			self.assertEqual(len(workspace.get_number_cards()), 3)
			self.assertTrue({
				"Processo Judicial", "Configurações DataJud", "Processos Judiciais"
			}.issubset({item["link_to"] for item in workspace.get_shortcuts()}))
			caixas = {card["label"]: card["links"] for card in workspace.get_links()}
			self.assertTrue({"Ética", "Judicial", "Configurações"}.issubset(caixas))
			self.assertEqual(caixas["Ética"][0]["link_to"], "Canal de Denuncias")
			self.assertEqual(caixas["Judicial"][0]["link_to"], "Processo Judicial")
			self.assertEqual(caixas["Configurações"][0]["label"], "Configurações de Processos Judiciais")
			self.assertEqual(caixas["Configurações"][0]["link_to"], "Configurações DataJud")
			self.assertIn("Relatórios", [block.custom_block_name for block in workspace.get_custom_blocks()])
			self.assertEqual(len(get_permitted_cards("Processos Judiciais")), 3)
			self.assertEqual(len(get_permitted_charts("Processos Judiciais")), 6)
			self.assertTrue(frappe.has_permission("Processo Judicial", "read"))
			frappe.get_single("Configurações DataJud").validate()
		finally:
			frappe.set_user(usuario_original)

	def test_usuario_juridico_ve_indicadores_sem_acesso_as_configuracoes(self):
		from frappe.desk.desktop import Workspace
		from frappe.desk.doctype.dashboard.dashboard import get_permitted_cards, get_permitted_charts

		usuario = "datajud-juridico-test@example.com"
		frappe.get_doc({
			"doctype": "User",
			"email": usuario,
			"first_name": "Usuário Jurídico",
			"send_welcome_email": 0,
			"user_type": "System User",
		}).insert(ignore_permissions=True)
		frappe.get_doc("User", usuario).add_roles("Usuário Jurídico")
		usuario_original = frappe.session.user
		try:
			frappe.set_user(usuario)
			workspace = Workspace({"name": "Jurídico"})
			self.assertEqual(len(workspace.get_number_cards()), 3)
			atalhos = {item["link_to"] for item in workspace.get_shortcuts()}
			self.assertIn("Processo Judicial", atalhos)
			self.assertIn("Processos Judiciais", atalhos)
			self.assertNotIn("Configurações DataJud", atalhos)
			caixas = {card["label"] for card in workspace.get_links()}
			self.assertIn("Judicial", caixas)
			self.assertNotIn("Configurações", caixas)
			self.assertIn("Relatórios", [block.custom_block_name for block in workspace.get_custom_blocks()])
			self.assertEqual(len(get_permitted_cards("Processos Judiciais")), 3)
			self.assertEqual(len(get_permitted_charts("Processos Judiciais")), 6)
			self.assertFalse(frappe.has_permission("Configurações DataJud", "read"))
		finally:
			frappe.set_user(usuario_original)

	def test_agendamento_e_falha_isolada(self):
		self.assertEqual(frappe.db.get_value(
			"Scheduled Job Type",
			{"method": "integracoes_customizadas.juridico.datajud.atualizar_processos_acompanhados"},
			"cron_format",
		), "0 3 * * 1-5")
		processos = [
			frappe._dict(numero_processo=NUMERO, tribunal="TRF1"),
			frappe._dict(numero_processo="1" * 20, tribunal="TRE-AC"),
		]
		with (
			patch.object(datajud, "_chave_publica", return_value="chave"),
			patch.object(datajud.frappe, "get_all", return_value=processos),
			patch.object(datajud.frappe, "enqueue") as enqueue,
		):
			datajud.atualizar_processos_acompanhados()
			self.assertEqual(datajud.frappe.get_all.call_args.kwargs["filters"], {
				"status_processo": "Em andamento"
			})
		self.assertEqual(enqueue.call_count, 2)
		self.assertTrue(all(call.kwargs["queue"] == "long" for call in enqueue.call_args_list))
		self.assertEqual({call.kwargs["alias"] for call in enqueue.call_args_list}, {"trf1", "tre-ac"})
		with (
			patch.object(datajud, "_ids_em_andamento", return_value={IDENTIFICADOR}),
			patch.object(datajud, "consultar_numero", side_effect=datajud.DataJudError("falha")),
			patch.object(datajud.frappe, "log_error") as log,
		):
			datajud.atualizar_um_processo(NUMERO, "trf1")
		self.assertEqual(log.call_count, 1)

	def test_status_manual_e_migracao(self):
		from integracoes_customizadas.juridico.setup import after_migrate

		identificador = "status-manual"
		numero = "7" * 20
		meta = frappe.get_meta("Processo Judicial")
		campo = meta.get_field("status_processo")
		self.assertEqual(campo.default, "Em andamento")
		self.assertEqual(campo.options, "Em andamento\nEncerrado")
		self.assertTrue(campo.in_list_view)
		self.assertTrue(campo.in_standard_filter)
		datajud._espelhar_ocorrencia(identificador, _fonte(identificador, numero))
		doc = frappe.get_doc("Processo Judicial", identificador)
		self.assertEqual(doc.status_processo, "Em andamento")
		doc.status_processo = "Encerrado"
		doc.save()
		datajud._espelhar_ocorrencia(identificador, _fonte(identificador, numero))
		doc.reload()
		self.assertEqual(doc.status_processo, "Encerrado")
		with patch.object(datajud, "consultar_numero", return_value=[
			(identificador, _fonte(identificador, numero))
		]):
			self.assertEqual(datajud.acompanhar_processo(numero, "trf1"), [
				{"name": identificador, "existente": True}
			])
		self.assertEqual(frappe.db.get_value("Processo Judicial", identificador, "status_processo"), "Encerrado")
		doc.status_processo = "Em andamento"
		doc.save()
		self.assertEqual(frappe.db.get_value("Processo Judicial", identificador, "status_processo"), "Em andamento")
		frappe.db.set_value("Processo Judicial", identificador, "status_processo", None)
		after_migrate()
		self.assertEqual(frappe.db.get_value("Processo Judicial", identificador, "status_processo"), "Em andamento")

	def test_agendamento_ignora_pares_encerrados(self):
		numero_ativo = "2" * 20
		numero_encerrado = "3" * 20
		datajud._espelhar_ocorrencia("agendamento-ativo", _fonte("agendamento-ativo", numero_ativo))
		datajud._espelhar_ocorrencia(
			"agendamento-encerrado-mesmo-par", _fonte("agendamento-encerrado-mesmo-par", numero_ativo)
		)
		fonte_outro = _fonte("agendamento-encerrado-outro-par", numero_encerrado)
		fonte_outro["tribunal"] = "TRE-AC"
		datajud._espelhar_ocorrencia("agendamento-encerrado-outro-par", fonte_outro)
		for nome in ("agendamento-encerrado-mesmo-par", "agendamento-encerrado-outro-par"):
			frappe.db.set_value("Processo Judicial", nome, "status_processo", "Encerrado")
		with patch.object(datajud, "_chave_publica", return_value="chave"), patch.object(
			datajud.frappe, "enqueue"
		) as enqueue:
			datajud.atualizar_processos_acompanhados()
		pares = [(call.kwargs["numero"], call.kwargs["alias"]) for call in enqueue.call_args_list]
		self.assertEqual(pares.count((datajud._numero_cnj_formatado(numero_ativo), "trf1")), 1)
		self.assertNotIn((datajud._numero_cnj_formatado(numero_encerrado), "tre-ac"), pares)

	def test_trabalho_enfileirado_para_processo_encerrado_nao_consulta(self):
		numero = "4" * 20
		identificador = "trabalho-encerrado"
		datajud._espelhar_ocorrencia(identificador, _fonte(identificador, numero))
		frappe.db.set_value("Processo Judicial", identificador, "status_processo", "Encerrado")
		with patch.object(datajud, "consultar_numero") as consultar:
			datajud.atualizar_um_processo(numero, "trf1")
		consultar.assert_not_called()

	def test_atualizacao_preserva_encerrados_e_ocorrencias_novas(self):
		numero = "5" * 20
		datajud._espelhar_ocorrencia("misto-ativo", _fonte("misto-ativo", numero))
		datajud._espelhar_ocorrencia("misto-encerrado", _fonte("misto-encerrado", numero))
		frappe.db.set_value("Processo Judicial", "misto-encerrado", "status_processo", "Encerrado")
		fonte_ativa = _fonte("misto-ativo", numero)
		fonte_ativa["classe"]["nome"] = "Classe atualizada"
		fonte_encerrada = _fonte("misto-encerrado", numero)
		fonte_encerrada["classe"]["nome"] = "Não deve ser gravada"
		with patch.object(datajud, "consultar_numero", return_value=[
			("misto-encerrado", fonte_encerrada), ("misto-ativo", fonte_ativa),
			("misto-novo", _fonte("misto-novo", numero))
		]):
			datajud.atualizar_um_processo(numero, "trf1")
		self.assertEqual(frappe.db.get_value("Processo Judicial", "misto-encerrado", "classe_nome"),
			"Procedimento do Juizado")
		self.assertEqual(frappe.db.get_value("Processo Judicial", "misto-ativo", "classe_nome"), "Classe atualizada")
		self.assertTrue(frappe.db.exists("Processo Judicial", "misto-novo"))

	def test_encerramento_durante_consulta_impede_atualizacao(self):
		numero = "6" * 20
		identificador = "encerrado-durante-consulta"
		datajud._espelhar_ocorrencia(identificador, _fonte(identificador, numero))
		fonte = _fonte(identificador, numero)
		fonte["classe"]["nome"] = "Não deve ser gravada"

		def consultar(*args):
			frappe.db.set_value("Processo Judicial", identificador, "status_processo", "Encerrado")
			return [(identificador, fonte), ("novo-durante-consulta", _fonte("novo-durante-consulta", numero))]

		with patch.object(datajud, "consultar_numero", side_effect=consultar):
			datajud.atualizar_um_processo(numero, "trf1")
		self.assertEqual(frappe.db.get_value("Processo Judicial", identificador, "classe_nome"),
			"Procedimento do Juizado")
		self.assertFalse(frappe.db.exists("Processo Judicial", "novo-durante-consulta"))

	def test_busca_manual_atualiza_apenas_ocorrencia_aberta_inclusive_encerrada(self):
		numero = "8" * 20
		identificador = "busca-manual-encerrado"
		outro = "busca-manual-outro"
		datajud._espelhar_ocorrencia(identificador, _fonte(identificador, numero))
		datajud._espelhar_ocorrencia(outro, _fonte(outro, numero))
		frappe.db.set_value("Processo Judicial", identificador, "status_processo", "Encerrado")
		fonte = _fonte(identificador, numero)
		fonte["movimentos"].append({
			"codigo": 51, "nome": "Conclusão", "dataHora": "2023-07-22T10:00:00.000Z"
		})
		fonte["classe"]["nome"] = "Classe atualizada"
		with patch.object(datajud, "consultar_numero", return_value=[
			(outro, _fonte(outro, numero)), (identificador, fonte),
		]):
			resultado = datajud.buscar_andamentos(identificador)
		self.assertEqual(resultado, {"novos_andamentos": 1, "total_andamentos": 2})
		doc = frappe.get_doc("Processo Judicial", identificador)
		self.assertEqual(doc.status_processo, "Encerrado")
		self.assertEqual(doc.classe_nome, "Classe atualizada")
		self.assertEqual(len(frappe.get_doc("Processo Judicial", outro).movimentos), 1)
		with patch.object(datajud, "consultar_numero", return_value=[(identificador, fonte)]):
			self.assertEqual(datajud.buscar_andamentos(identificador)["novos_andamentos"], 0)

	def test_busca_manual_sem_ocorrencia_preserva_dados(self):
		identificador = "busca-manual-ausente"
		numero = "9" * 20
		datajud._espelhar_ocorrencia(identificador, _fonte(identificador, numero))
		with patch.object(datajud, "consultar_numero", return_value=[]):
			with self.assertRaises(frappe.ValidationError):
				datajud.buscar_andamentos(identificador)
		self.assertEqual(len(frappe.get_doc("Processo Judicial", identificador).movimentos), 1)

	def test_conexoes_das_partes_filtram_o_tipo_correto(self):
		from frappe.desk.notifications import get_dynamic_link_filters

		for tipo_parte in ("Employee", "Customer", "Supplier"):
			with self.subTest(tipo_parte=tipo_parte):
				dados = frappe.get_meta(tipo_parte).get_dashboard_data()
				self.assertIn("Processo Judicial", [
					item for grupo in dados.transactions for item in grupo["items"]
				])
				self.assertEqual(dados.non_standard_fieldnames["Processo Judicial"], "parte")
				self.assertEqual(get_dynamic_link_filters("Processo Judicial", dados, "parte"), {
					"tipo_parte": tipo_parte
				})

	def test_conexao_do_colaborador_localiza_seus_processos(self):
		from frappe.desk.notifications import get_open_count

		colaborador = frappe.get_doc({
			"doctype": "Employee",
			"naming_series": "EMP-",
			"first_name": "Colaborador Jurídico",
			"company": frappe.get_all("Company", pluck="name", limit=1)[0],
			"gender": frappe.get_all("Gender", pluck="name", limit=1)[0],
			"date_of_birth": "1990-05-08",
			"date_of_joining": "2020-01-01",
			"status": "Active",
		}).insert(ignore_mandatory=True)
		identificador = "processo-colaborador-conexao"
		datajud._espelhar_ocorrencia(identificador, _fonte(identificador, "3" * 20))
		processo = frappe.get_doc("Processo Judicial", identificador)
		processo.tipo_parte = "Employee"
		processo.parte = colaborador.name
		processo.save()
		conexoes = get_open_count("Employee", colaborador.name)["count"]["external_links_found"]
		self.assertIn({"doctype": "Processo Judicial", "count": 1, "open_count": 0}, conexoes)

	def test_processo_relacionado_aparece_nas_conexoes_e_resiste_ao_datajud(self):
		from frappe.desk.notifications import get_open_count

		origem = "processo-relacionado-origem"
		destino = "processo-relacionado-destino"
		datajud._espelhar_ocorrencia(origem, _fonte(origem, "1" * 20))
		datajud._espelhar_ocorrencia(destino, _fonte(destino, "2" * 20))
		doc = frappe.get_doc("Processo Judicial", origem)
		doc.processo_relacionado = origem
		with self.assertRaises(frappe.ValidationError):
			doc.save()
		doc.reload()
		doc.processo_relacionado = destino
		doc.save()
		datajud._espelhar_ocorrencia(origem, _fonte(origem, "1" * 20))
		self.assertEqual(frappe.db.get_value("Processo Judicial", origem, "processo_relacionado"), destino)
		meta = frappe.get_meta("Processo Judicial")
		self.assertTrue(meta.get_field("aba_conexoes").show_dashboard)
		self.assertEqual(meta.get_field("processo_relacionado").options, "Processo Judicial")
		campos = [campo.fieldname for campo in meta.fields]
		self.assertGreater(campos.index("processo_relacionado"), campos.index("aba_conexoes"))
		conexoes = get_open_count("Processo Judicial", destino)["count"]["external_links_found"]
		self.assertIn({"doctype": "Processo Judicial", "count": 1, "open_count": 0}, conexoes)
