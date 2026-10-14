import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe
import requests

from integracoes_customizadas.whatsapp import conector, webhook
from integracoes_customizadas.whatsapp.conector import (
	EnvioRejeitado,
	EvolutionIndisponivel,
	NumeroInvalido,
	normalizar_numero_br,
)

if not getattr(frappe.local, "flags", None):
	frappe.local.flags = frappe._dict(in_test=True)

CHAVE = "chave-super-secreta"


def settings(**extra):
	dados = {
		"server_url": "https://evo.exemplo.com",
		"instance_name": "bhcl",
		"ativo": 1,
		"timeout_conexao_s": 5,
		"timeout_leitura_s": 15,
		"delay_min_s": 2,
		"delay_max_s": 6,
		"verificar_numero_antes": 1,
	}
	dados.update(extra)
	obj = SimpleNamespace(**dados)
	obj.get = lambda campo, default=None: dados.get(campo, default)
	obj.get_password = lambda *a, **k: CHAVE
	return obj


def resposta(status=200, corpo=None):
	r = MagicMock()
	r.status_code = status
	r.json.return_value = corpo
	return r


class Base(unittest.TestCase):
	def setUp(self):
		self.cfg = settings()
		patcher = patch("integracoes_customizadas.whatsapp.api.get_settings", side_effect=lambda: self.cfg)
		patcher.start()
		self.addCleanup(patcher.stop)
		log = patch.object(conector.frappe, "log_error")
		self.log = log.start()
		self.addCleanup(log.stop)
		cache = patch.object(conector.frappe, "cache", MagicMock())
		self.cache = cache.start()
		self.cache.get_value.return_value = None
		self.cache.hget.return_value = {}  # _() consulta o mesmo cache; sem traduções cai no texto original
		self.addCleanup(cache.stop)
		sleep = patch.object(conector.time, "sleep")
		self.sleep = sleep.start()
		self.addCleanup(sleep.stop)


class TestNormalizarNumero(unittest.TestCase):
	def test_tabela(self):
		casos = {
			"(11) 99999-1234": "5511999991234",
			"11999991234": "5511999991234",
			"+55 11 99999-1234": "5511999991234",
			"5511999991234": "5511999991234",
			"011 99999-1234": "5511999991234",
			"0 11 99999-1234": "5511999991234",
			"(11) 3333-4444": "551133334444",
			"55 11 3333-4444": "551133334444",
			"(55) 99999-1234": "5555999991234",  # DDD 55 (RS) não é confundido com o código do país
			"(11) 8888-7777": "551188887777",  # celular antigo sem o nono dígito
		}
		for bruto, esperado in casos.items():
			with self.subTest(bruto=bruto):
				self.assertEqual(normalizar_numero_br(bruto), esperado)

	def test_invalidos(self):
		for bruto in (
			None,
			"",
			"abc",
			"123",
			"(10) 99999-1234",
			"(11) 89999-1234",
			"11999991234 ramal 2",
			"55119999912345",
			"(11) 0333-4444",
		):
			with self.subTest(bruto=bruto):
				self.assertIsNone(normalizar_numero_br(bruto))


class TestEstadoConexao(Base):
	@patch.object(conector.requests, "request")
	def test_conectado(self, req):
		req.return_value = resposta(200, {"instance": {"instanceName": "bhcl", "state": "open"}})
		self.assertEqual(conector.estado_conexao(), {"conectado": True, "estado": "open"})
		self.assertEqual(req.call_args.kwargs["headers"]["apikey"], CHAVE)
		self.assertEqual(req.call_args.kwargs["timeout"], (5, 15))

	@patch.object(conector.requests, "request")
	def test_desconectado(self, req):
		req.return_value = resposta(200, {"instance": {"state": "close"}})
		self.assertEqual(conector.estado_conexao(), {"conectado": False, "estado": "close"})

	@patch.object(conector.requests, "request")
	def test_get_repete_uma_vez_e_depois_desiste(self, req):
		req.side_effect = requests.Timeout()
		self.assertEqual(conector.estado_conexao(), {"conectado": False, "estado": "indisponivel"})
		self.assertEqual(req.call_count, 2)

	@patch.object(conector.requests, "request")
	def test_get_recupera_na_segunda_tentativa(self, req):
		req.side_effect = [requests.ConnectionError(), resposta(200, {"instance": {"state": "open"}})]
		self.assertTrue(conector.estado_conexao()["conectado"])

	@patch.object(conector.requests, "request")
	def test_instancia_inexistente_nao_levanta(self, req):
		req.return_value = resposta(404, {})
		self.assertFalse(conector.estado_conexao()["conectado"])
		self.assertEqual(req.call_count, 1)  # 4xx não é repetido


class TestVerificarNumero(Base):
	@patch.object(conector.requests, "request")
	def test_existe_usa_numero_canonico(self, req):
		req.return_value = resposta(
			200, [{"exists": True, "jid": "551188887777@s.whatsapp.net", "number": "551188887777"}]
		)
		r = conector.verificar_numero("(11) 98888-7777")
		self.assertEqual(r, {"existe": True, "numero": "551188887777", "jid": "551188887777@s.whatsapp.net"})
		self.assertEqual(req.call_args.kwargs["json"], {"numbers": ["5511988887777"]})

	@patch.object(conector.requests, "request")
	def test_inexistente(self, req):
		req.return_value = resposta(200, [{"exists": False, "jid": "x@s.whatsapp.net", "number": "5511"}])
		self.assertEqual(
			conector.verificar_numero("11999991234"), {"existe": False, "numero": None, "jid": None}
		)

	def test_numero_malformado(self):
		with self.assertRaises(NumeroInvalido):
			conector.verificar_numero("123")


class TestEnviarTexto(Base):
	def _ok(self, req, id_="3EB0ABC"):
		req.side_effect = [
			resposta(
				200, [{"exists": True, "jid": "5511999991234@s.whatsapp.net", "number": "5511999991234"}]
			),
			resposta(201, {"key": {"id": id_}, "status": "PENDING"}),
		]

	@patch.object(conector.requests, "request")
	def test_sucesso(self, req):
		self._ok(req)
		r = conector.enviar_texto("(11) 99999-1234", "olá", prioridade="alta")
		self.assertEqual(r, {"ok": True, "message_id": "3EB0ABC", "status": "PENDING", "erro": None})
		envio = req.call_args_list[1]
		self.assertEqual(
			envio.kwargs["json"], {"number": "5511999991234", "text": "olá", "linkPreview": True}
		)
		self.assertTrue(envio.args[1].endswith("/message/sendText/bhcl"))

	@patch.object(conector.requests, "request")
	def test_prioridade_alta_nao_espera_e_normal_espera(self, req):
		self._ok(req)
		conector.enviar_texto("11999991234", "x", prioridade="alta")
		self.sleep.assert_not_called()
		self._ok(req)
		with patch.object(conector.time, "time", return_value=1000.0):
			self.cache.get_value.return_value = 1000.0
			with patch.object(conector.random, "uniform", return_value=4.0):
				conector.enviar_texto("11999991234", "x")
		self.sleep.assert_called_once_with(4.0)
		self.cache.set_value.assert_called_with(conector.CHAVE_ULTIMO_ENVIO, 1004.0, expires_in_sec=3600)

	@patch.object(conector.requests, "request")
	def test_timeout_no_envio_nao_repete(self, req):
		req.side_effect = [
			resposta(200, [{"exists": True, "number": "5511999991234"}]),
			requests.Timeout(),
		]
		with self.assertRaises(EvolutionIndisponivel):
			conector.enviar_texto("11999991234", "x", prioridade="alta")
		self.assertEqual(req.call_count, 2)  # 1 verificação + 1 envio, sem retry do POST

	@patch.object(conector.requests, "request")
	def test_401(self, req):
		req.return_value = resposta(401, {})
		with self.assertRaises(EnvioRejeitado):
			conector.enviar_texto("11999991234", "x", prioridade="alta")

	@patch.object(conector.requests, "request")
	def test_404_instancia(self, req):
		req.return_value = resposta(404, {})
		with self.assertRaises(EnvioRejeitado) as ctx:
			conector.enviar_texto("11999991234", "x", prioridade="alta")
		self.assertIn("Instância", str(ctx.exception))

	@patch.object(conector.requests, "request")
	def test_numero_inexistente_no_whatsapp(self, req):
		req.return_value = resposta(200, [{"exists": False}])
		with self.assertRaises(NumeroInvalido):
			conector.enviar_texto("11999991234", "x", prioridade="alta")
		self.assertEqual(req.call_count, 1)  # nada foi enviado

	@patch.object(conector.requests, "request")
	def test_instancia_desconectada_vira_indisponivel(self, req):
		req.return_value = resposta(503, {})
		with self.assertRaises(EvolutionIndisponivel):
			conector.enviar_texto("11999991234", "x", prioridade="alta")

	def test_numero_malformado(self):
		with self.assertRaises(NumeroInvalido):
			conector.enviar_texto("abc", "x")

	@patch.object(conector.requests, "request")
	def test_sem_verificacao_previa(self, req):
		self.cfg = settings(verificar_numero_antes=0)
		req.return_value = resposta(201, {"key": {"id": "A1"}})
		r = conector.enviar_texto("(11) 99999-1234", "x", prioridade="alta")
		self.assertEqual((r["message_id"], req.call_count), ("A1", 1))

	@patch.object(conector.requests, "request")
	def test_log_nao_vaza_chave_texto_nem_numero(self, req):
		req.side_effect = [resposta(200, [{"exists": True, "number": "5511999991234"}]), requests.Timeout()]
		with self.assertRaises(EvolutionIndisponivel):
			conector.enviar_texto("11999991234", "Seu código é 123456", prioridade="alta")
		registrado = str(self.log.call_args)
		for segredo in (CHAVE, "123456", "5511999991234", "999991234"):
			self.assertNotIn(segredo, registrado)
		self.assertIn("***1234", registrado)

	def test_conector_desativado_ou_nao_configurado(self):
		with patch("integracoes_customizadas.whatsapp.api.get_settings", side_effect=frappe.ValidationError):
			with self.assertRaises(EvolutionIndisponivel):
				conector.enviar_texto("11999991234", "x")


EVENTO = {"message_id": "A1", "status": "entregue", "ocorrido_em": datetime(2026, 10, 13), "bruto": {}}


class TestWebhook(unittest.TestCase):
	def test_despacha_para_todos_os_handlers_mesmo_com_falha(self):
		chamados = []
		handlers = {"a.b": lambda e: chamados.append(("a", e)), "c.d": MagicMock(side_effect=RuntimeError)}
		with (
			patch.object(webhook.frappe, "get_hooks", return_value=list(handlers)),
			patch.object(webhook.frappe, "get_attr", side_effect=lambda p: handlers[p]),
			patch.object(webhook.frappe, "log_error") as log,
		):
			self.assertEqual(webhook.despachar_evento(EVENTO), 1)
		self.assertEqual(chamados, [("a", EVENTO)])
		log.assert_called_once()

	def test_evento_fora_do_contrato(self):
		for ruim in ({}, {**EVENTO, "status": "lixo"}, {**EVENTO, "message_id": ""}):
			with self.assertRaises(ValueError):
				webhook.despachar_evento(ruim)

	def test_endpoint_desligado_responde_501(self):
		frappe.local.response = frappe._dict()
		with patch.object(webhook.frappe.db, "get_single_value", return_value=0):
			webhook.webhook_evolution()
		self.assertEqual(frappe.local.response["http_status_code"], 501)
