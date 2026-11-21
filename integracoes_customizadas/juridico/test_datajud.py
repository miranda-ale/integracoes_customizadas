"""Cobertura da instrumentação de log, classificação de erro e circuit breaker do DataJud.

Simula as respostas da API pública (200, 403, 429, 500 e timeout) mockando `requests.post`; nenhum
teste aqui faz uma chamada de rede real.
"""

from unittest.mock import Mock, patch

import frappe
import requests
from frappe.tests.utils import FrappeTestCase

from integracoes_customizadas.juridico import datajud


def _resposta(status_code, corpo=None, json_valido=True):
	mock = Mock()
	mock.status_code = status_code
	mock.text = corpo if corpo is not None else '{"hits": {"hits": []}}'
	if json_valido:
		mock.json.return_value = {"hits": {"hits": []}}
	else:
		mock.json.side_effect = ValueError("corpo não é JSON")
	return mock


class TestClassificacaoDeErros(FrappeTestCase):
	def test_200_retorna_conteudo_sem_gravar_log(self):
		with patch.object(datajud.requests, "post", return_value=_resposta(200)):
			conteudo = datajud._post("stj", {}, "chave-publica-1234")
		self.assertEqual(conteudo, {"hits": {"hits": []}})
		self.assertEqual(frappe.db.count("DataJud Sync Log"), 0)

	def test_403_classifica_como_autenticacao_e_mascara_a_chave(self):
		with patch.object(datajud.requests, "post", return_value=_resposta(403, corpo="security_exception")):
			with self.assertRaises(datajud.DataJudError) as contexto:
				datajud._post("stj", {}, "chave-publica-1234", numero_processo="123")
		self.assertEqual(contexto.exception.tipo_erro, datajud.ERRO_AUTENTICACAO)
		log = frappe.get_last_doc("DataJud Sync Log")
		self.assertEqual(log.tipo_erro, datajud.ERRO_AUTENTICACAO)
		self.assertEqual(log.status_http, 403)
		self.assertEqual(log.api_key_mascarada, "chav…")
		self.assertNotIn("publica-1234", log.api_key_mascarada)
		self.assertIn("security_exception", log.corpo_resposta)

	def test_429_classifica_como_limite_de_requisicoes(self):
		with patch.object(datajud.requests, "post", return_value=_resposta(429)):
			with self.assertRaises(datajud.DataJudError) as contexto:
				datajud._post("stj", {}, "chave", tentativas=1)
		self.assertEqual(contexto.exception.tipo_erro, datajud.ERRO_LIMITE)

	def test_500_classifica_como_indisponivel(self):
		with patch.object(datajud.requests, "post", return_value=_resposta(500)):
			with self.assertRaises(datajud.DataJudError) as contexto:
				datajud._post("stj", {}, "chave", tentativas=1)
		self.assertEqual(contexto.exception.tipo_erro, datajud.ERRO_INDISPONIVEL)

	def test_timeout_classifica_como_indisponivel(self):
		with patch.object(datajud.requests, "post", side_effect=requests.Timeout("demorou demais")):
			with self.assertRaises(datajud.DataJudError) as contexto:
				datajud._post("stj", {}, "chave", tentativas=1)
		self.assertEqual(contexto.exception.tipo_erro, datajud.ERRO_INDISPONIVEL)

	def test_404_classifica_como_nao_encontrado(self):
		with patch.object(datajud.requests, "post", return_value=_resposta(404)):
			with self.assertRaises(datajud.DataJudError) as contexto:
				datajud._post("stj", {}, "chave", tentativas=1)
		self.assertEqual(contexto.exception.tipo_erro, datajud.ERRO_NAO_ENCONTRADO)

	def test_json_invalido_classifica_como_dados_invalidos(self):
		with patch.object(datajud.requests, "post", return_value=_resposta(200, json_valido=False)):
			with self.assertRaises(datajud.DataJudError) as contexto:
				datajud._post("stj", {}, "chave")
		self.assertEqual(contexto.exception.tipo_erro, datajud.ERRO_DADOS_INVALIDOS)


class TestMascaramentoDeChave(FrappeTestCase):
	def test_mostra_so_os_4_primeiros_caracteres(self):
		self.assertEqual(datajud._mascarar_chave("ABCDEFGH"), "ABCD…")

	def test_chave_curta_fica_totalmente_oculta(self):
		self.assertEqual(datajud._mascarar_chave("AB"), "…")

	def test_chave_vazia(self):
		self.assertIsNone(datajud._mascarar_chave(None))
		self.assertIsNone(datajud._mascarar_chave(""))


class TestColetorAgrupaPorExecucao(FrappeTestCase):
	def test_agrupa_contagem_e_processos_por_tipo_de_erro(self):
		coletor = datajud._ColetorErros()
		for numero in ("1111", "2222", "1111"):
			coletor.registrar(
				datajud.ERRO_INDISPONIVEL,
				numero_processo=numero,
				amostra={"tribunal": "stj", "status_http": 500},
			)
		coletor.registrar(datajud.ERRO_AUTENTICACAO, numero_processo="3333", amostra={"status_http": 403})

		self.assertEqual(coletor.grupos[datajud.ERRO_INDISPONIVEL]["contagem"], 3)
		self.assertEqual(coletor.grupos[datajud.ERRO_INDISPONIVEL]["processos"], ["1111", "2222"])
		self.assertEqual(coletor.tipo_predominante(), datajud.ERRO_INDISPONIVEL)

		coletor.persistir()
		logs = frappe.get_all(
			"DataJud Sync Log", filters={"execucao": coletor.execucao}, fields=["tipo_erro", "contagem"]
		)
		self.assertEqual(len(logs), 2)
		contagens = {linha.tipo_erro: linha.contagem for linha in logs}
		self.assertEqual(contagens[datajud.ERRO_INDISPONIVEL], 3)
		self.assertEqual(contagens[datajud.ERRO_AUTENTICACAO], 1)


class TestCircuitBreaker(FrappeTestCase):
	def _config_zerada(self):
		config = frappe.get_single("Configurações DataJud")
		config.circuito_aberto = 0
		config.circuito_tipo_falha = None
		config.circuito_motivo = None
		config.circuito_aberto_em = None
		config.circuito_nivel_backoff = 0
		config.circuito_proxima_tentativa = None
		config.falhas_consecutivas = 0
		return config

	def test_abre_apos_3_falhas_seguidas_de_autenticacao(self):
		config = self._config_zerada()
		with patch.object(datajud, "_notificar_administradores") as notificar:
			datajud._abrir_ou_manter_circuito(config, datajud.ERRO_AUTENTICACAO)
			datajud._abrir_ou_manter_circuito(config, datajud.ERRO_AUTENTICACAO)
			self.assertFalse(config.circuito_aberto)
			notificar.assert_not_called()
			datajud._abrir_ou_manter_circuito(config, datajud.ERRO_AUTENTICACAO)
		self.assertTrue(config.circuito_aberto)
		self.assertEqual(config.circuito_tipo_falha, datajud.ERRO_AUTENTICACAO)
		notificar.assert_called_once()
		# Erro de autenticação não agenda nova tentativa sozinho.
		self.assertIsNone(config.circuito_proxima_tentativa)
		self.assertFalse(datajud._circuito_permite_execucao(config))

	def test_contagem_acumula_entre_execucoes_persistidas(self):
		"""Regressão: cada execução do cron recarrega a configuração; a contagem não pode zerar a cada uma."""
		config = self._config_zerada()
		config.api_key = "chave-de-teste"
		config.save(ignore_permissions=True)
		with patch.object(datajud, "_notificar_administradores") as notificar:
			for esperado in (1, 2):
				config = frappe.get_single("Configurações DataJud")
				datajud._abrir_ou_manter_circuito(config, datajud.ERRO_AUTENTICACAO)
				config.save(ignore_permissions=True)
				self.assertEqual(frappe.get_single("Configurações DataJud").falhas_consecutivas, esperado)
				self.assertFalse(frappe.get_single("Configurações DataJud").circuito_aberto)
			notificar.assert_not_called()
			config = frappe.get_single("Configurações DataJud")
			datajud._abrir_ou_manter_circuito(config, datajud.ERRO_AUTENTICACAO)
			config.save(ignore_permissions=True)
		self.assertTrue(frappe.get_single("Configurações DataJud").circuito_aberto)
		notificar.assert_called_once()

	def test_abre_apos_5_falhas_seguidas_de_indisponibilidade_com_backoff(self):
		config = self._config_zerada()
		with patch.object(datajud, "_notificar_administradores"):
			for _ in range(5):
				datajud._abrir_ou_manter_circuito(config, datajud.ERRO_INDISPONIVEL)
		self.assertTrue(config.circuito_aberto)
		self.assertIsNotNone(config.circuito_proxima_tentativa)
		# Antes da próxima tentativa, o circuito continua fechando a porta.
		self.assertFalse(datajud._circuito_permite_execucao(config))
		# Depois da janela de backoff, a execução pode tentar de novo (half-open).
		config.circuito_proxima_tentativa = frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=-1)
		self.assertTrue(datajud._circuito_permite_execucao(config))

	def test_tipo_de_falha_diferente_reinicia_a_contagem(self):
		config = self._config_zerada()
		with patch.object(datajud, "_notificar_administradores"):
			datajud._abrir_ou_manter_circuito(config, datajud.ERRO_AUTENTICACAO)
			datajud._abrir_ou_manter_circuito(config, datajud.ERRO_AUTENTICACAO)
			datajud._abrir_ou_manter_circuito(config, datajud.ERRO_LIMITE)
		self.assertEqual(config.falhas_consecutivas, 1)
		self.assertFalse(config.circuito_aberto)

	def test_fechar_circuito_reseta_tudo_e_notifica_volta_ao_normal(self):
		config = self._config_zerada()
		with patch.object(datajud, "_notificar_administradores"):
			for _ in range(3):
				datajud._abrir_ou_manter_circuito(config, datajud.ERRO_AUTENTICACAO)
		self.assertTrue(config.circuito_aberto)
		with patch.object(datajud, "_notificar_administradores") as notificar:
			datajud._fechar_circuito_se_necessario(config)
		notificar.assert_called_once()
		self.assertFalse(config.circuito_aberto)
		self.assertIsNone(config.circuito_tipo_falha)
		self.assertEqual(config.falhas_consecutivas, 0)

	def test_trocar_a_chave_reabre_o_circuito_de_autenticacao(self):
		config = frappe.get_single("Configurações DataJud")
		config.api_key = "chave-antiga-0000"
		config.save(ignore_permissions=True)
		with patch.object(datajud, "_notificar_administradores"):
			for _ in range(3):
				datajud._abrir_ou_manter_circuito(config, datajud.ERRO_AUTENTICACAO)
		config.save(ignore_permissions=True)
		self.assertTrue(frappe.get_single("Configurações DataJud").circuito_aberto)

		nova_config = frappe.get_single("Configurações DataJud")
		nova_config.api_key = "chave-nova-1111"
		nova_config.save(ignore_permissions=True)

		self.assertFalse(frappe.get_single("Configurações DataJud").circuito_aberto)
