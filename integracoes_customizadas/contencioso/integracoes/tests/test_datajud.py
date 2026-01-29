# Copyright (c) 2026
# Tests for integração API Datajud

import unittest
from unittest.mock import MagicMock, patch

from integracoes_customizadas.contencioso.integracoes.datajud import (
	cnj_to_tribunal_alias,
	_normalize_cnj,
	mapear_resposta_para_form,
	_nivel_sigilo_datajud_to_doc,
	_parse_data_ajuizamento,
	_parse_datetime,
)


class TestCnjNormalize(unittest.TestCase):
	def test_normalize_empty(self):
		self.assertEqual(_normalize_cnj(""), "")
		self.assertEqual(_normalize_cnj(None), "")

	def test_normalize_digits_only(self):
		self.assertEqual(_normalize_cnj("12345678901234567890"), "12345678901234567890")

	def test_normalize_strips_non_digits(self):
		self.assertEqual(_normalize_cnj("1234-56.7890.1.23.4567"), "12345678901234567")

	def test_normalize_caps_at_20(self):
		self.assertEqual(len(_normalize_cnj("1" * 25)), 20)


class TestCnjToTribunalAlias(unittest.TestCase):
	def test_trt2(self):
		# J=5 (Justiça do Trabalho), TR=02 -> trt2
		numero = "000000000020255020000"
		self.assertEqual(len(numero), 20)
		self.assertEqual(cnj_to_tribunal_alias(numero), "api_publica_trt2")

	def test_tjsp(self):
		# J=8 (Estadual), TR=26 (SP)
		numero = "000000000020258260000"
		self.assertEqual(cnj_to_tribunal_alias(numero), "api_publica_tjsp")

	def test_trf1(self):
		# J=4 (Federal), TR=01
		numero = "000000000020254010000"
		self.assertEqual(cnj_to_tribunal_alias(numero), "api_publica_trf1")

	def test_less_than_20_returns_none(self):
		self.assertIsNone(cnj_to_tribunal_alias("1234567890123456789"))

	def test_formatted_input_normalized(self):
		# input com formatação é normalizado internamente
		numero = "0000000-00.2025.5.02.0000"
		alias = cnj_to_tribunal_alias(numero)
		self.assertEqual(alias, "api_publica_trt2")


class TestNivelSigilo(unittest.TestCase):
	def test_0_publico(self):
		self.assertEqual(_nivel_sigilo_datajud_to_doc(0), "Publico")

	def test_1_restrito(self):
		self.assertEqual(_nivel_sigilo_datajud_to_doc(1), "Restrito")

	def test_2_5_sigiloso(self):
		self.assertEqual(_nivel_sigilo_datajud_to_doc(2), "Sigiloso")
		self.assertEqual(_nivel_sigilo_datajud_to_doc(5), "Sigiloso")

	def test_none_publico(self):
		self.assertEqual(_nivel_sigilo_datajud_to_doc(None), "Publico")


class TestParseData(unittest.TestCase):
	def test_parse_data_iso(self):
		self.assertEqual(_parse_data_ajuizamento("2025-01-15T00:00:00"), "2025-01-15")

	def test_parse_data_compact(self):
		self.assertEqual(_parse_data_ajuizamento("20250115"), "2025-01-15")

	def test_parse_datetime_iso(self):
		self.assertEqual(_parse_datetime("2025-01-15T12:30:00"), "2025-01-15 12:30:00")

	def test_parse_datetime_compact(self):
		self.assertEqual(_parse_datetime("20250115123000"), "2025-01-15 12:30:00")


class TestMapearRespostaParaForm(unittest.TestCase):
	@patch("integracoes_customizadas.contencioso.integracoes.datajud.frappe")
	def test_mapear_hit_minimo(self, mock_frappe):
		dt = MagicMock()
		dt.strftime.return_value = "2025-01-15 12:00:00"
		mock_frappe.utils.now_datetime.return_value = dt
		hit = {
			"numeroProcesso": "000000000020255020000",
			"tribunal": "TRT2",
			"dataAjuizamento": "2025-01-10T00:00:00",
			"nivelSigilo": 0,
			"classe": {"nome": "Reclamação Trabalhista"},
			"assuntos": [{"nome": "Horas extras"}],
			"orgaoJulgador": {"nome": "1ª Vara do Trabalho"},
			"movimentos": [
				{"dataHora": "2025-01-15T10:00:00", "nome": "Distribuição"},
			],
			"id": "TRT2_123_G1_456_000000000020255020000",
		}
		payload = mapear_resposta_para_form(hit, "000000000020255020000")
		self.assertIn("processo", payload)
		self.assertIn("cj_eventos", payload)
		self.assertIn("cj_integracoes", payload)
		self.assertEqual(payload["processo"]["cj_numero_cnj"], "000000000020255020000")
		self.assertEqual(payload["processo"]["cj_tribunal"], "TRT2")
		self.assertEqual(payload["processo"]["cj_data_distribuicao"], "2025-01-10")
		self.assertEqual(payload["processo"]["cj_classe"], "Reclamação Trabalhista")
		self.assertEqual(payload["processo"]["cj_assuntos"], "Horas extras")
		self.assertEqual(payload["processo"]["cj_vara_foro"], "1ª Vara do Trabalho")
		self.assertEqual(payload["processo"]["cj_nivel_sigilo"], "Publico")
		self.assertEqual(len(payload["cj_eventos"]), 1)
		self.assertEqual(payload["cj_eventos"][0]["cj_origem"], "Integração")
		self.assertEqual(payload["cj_eventos"][0]["cj_tipo_evento"], "Movimento")
		self.assertEqual(payload["cj_eventos"][0]["cj_resumo"], "Distribuição")
		self.assertEqual(len(payload["cj_integracoes"]), 1)
		self.assertEqual(payload["cj_integracoes"][0]["cj_provedor"], "DataJud")
		self.assertEqual(payload["cj_integracoes"][0]["cj_status_sync"], "OK")
