# Copyright (c) 2026
# Integração API Pública Datajud (CNJ) - https://datajud-wiki.cnj.jus.br/

import re
import logging
from typing import Optional

import frappe

try:
	import requests
except ImportError:
	requests = None

logger = logging.getLogger("contencioso")

BASE_URL = "https://api-publica.datajud.cnj.jus.br/"
REQUEST_TIMEOUT = 30

# CNJ: 20 dígitos — posições 1-7 seq, 8-9 DV, 10-13 ano, 14 = J (segmento), 15-16 = TR (tribunal).
# Mapeamento (segmento, tr) -> alias do índice (sem prefixo api_publica_).
# Fontes: https://datajud-wiki.cnj.jus.br/api-publica/endpoints/
SEGMENT_TR_TO_ALIAS = {
	# Tribunais Superiores (J=1 STF, 2 CNJ, 3 STJ, 4 TST? 5 TSE? 6 STM?) — usar códigos conforme CNJ
	(3, 0): "stj",   # STJ
	(4, 0): "tst",   # TST (ou segmento 5)
	(5, 0): "tst",   # TST
	(6, 0): "tse",   # TSE
	(7, 0): "stm",   # STM
	# Justiça Federal (J=4): TR 01-06
	(4, 1): "trf1",
	(4, 2): "trf2",
	(4, 3): "trf3",
	(4, 4): "trf4",
	(4, 5): "trf5",
	(4, 6): "trf6",
	# Justiça do Trabalho (J=5): TR 01-24
	(5, 1): "trt1",
	(5, 2): "trt2",
	(5, 3): "trt3",
	(5, 4): "trt4",
	(5, 5): "trt5",
	(5, 6): "trt6",
	(5, 7): "trt7",
	(5, 8): "trt8",
	(5, 9): "trt9",
	(5, 10): "trt10",
	(5, 11): "trt11",
	(5, 12): "trt12",
	(5, 13): "trt13",
	(5, 14): "trt14",
	(5, 15): "trt15",
	(5, 16): "trt16",
	(5, 17): "trt17",
	(5, 18): "trt18",
	(5, 19): "trt19",
	(5, 20): "trt20",
	(5, 21): "trt21",
	(5, 22): "trt22",
	(5, 23): "trt23",
	(5, 24): "trt24",
	# Justiça Eleitoral (J=6): TRE por UF (ordem: AC, AL, AM, AP, BA, CE, DF, ES, GO, MA, MG, MS, MT, PA, PB, PE, PI, PR, RJ, RN, RO, RR, RS, SC, SE, SP, TO)
	(6, 1): "tre-ac",
	(6, 2): "tre-al",
	(6, 3): "tre-am",
	(6, 4): "tre-ap",
	(6, 5): "tre-ba",
	(6, 6): "tre-ce",
	(6, 7): "tre-dft",
	(6, 8): "tre-es",
	(6, 9): "tre-go",
	(6, 10): "tre-ma",
	(6, 11): "tre-mg",
	(6, 12): "tre-ms",
	(6, 13): "tre-mt",
	(6, 14): "tre-pa",
	(6, 15): "tre-pb",
	(6, 16): "tre-pe",
	(6, 17): "tre-pi",
	(6, 18): "tre-pr",
	(6, 19): "tre-rj",
	(6, 20): "tre-rn",
	(6, 21): "tre-ro",
	(6, 22): "tre-rr",
	(6, 23): "tre-rs",
	(6, 24): "tre-sc",
	(6, 25): "tre-se",
	(6, 26): "tre-sp",
	(6, 27): "tre-to",
	# Justiça Estadual (J=8): TJ por UF mesma ordem
	(8, 1): "tjac",
	(8, 2): "tjal",
	(8, 3): "tjam",
	(8, 4): "tjap",
	(8, 5): "tjba",
	(8, 6): "tjce",
	(8, 7): "tjdft",
	(8, 8): "tjes",
	(8, 9): "tjgo",
	(8, 10): "tjma",
	(8, 11): "tjmg",
	(8, 12): "tjms",
	(8, 13): "tjmt",
	(8, 14): "tjpa",
	(8, 15): "tjpb",
	(8, 16): "tjpe",
	(8, 17): "tjpi",
	(8, 18): "tjpr",
	(8, 19): "tjrj",
	(8, 20): "tjrn",
	(8, 21): "tjro",
	(8, 22): "tjrr",
	(8, 23): "tjrs",
	(8, 24): "tjsc",
	(8, 25): "tjse",
	(8, 26): "tjsp",
	(8, 27): "tjto",
	# Justiça Militar Estadual (J=9)
	(9, 1): "tjmmg",
	(9, 2): "tjmrs",
	(9, 3): "tjmsp",
}


def _normalize_cnj(numero_cnj: str) -> str:
	"""Retorna apenas os 20 primeiros dígitos do número CNJ."""
	if not numero_cnj:
		return ""
	digits = re.sub(r"\D", "", str(numero_cnj))
	return digits[:20]


def get_api_key() -> Optional[str]:
	"""Obtém a chave da API Datajud (site_config ou DocType). Nunca retorna valor default em código."""
	key = frappe.conf.get("datajud_api_key")
	if key:
		return key.strip()
	# Opcional: DocType "Configurações Contencioso" com campo datajud_api_key
	try:
		doc = frappe.get_single("Configuracoes Contencioso")
		if doc and getattr(doc, "datajud_api_key", None):
			return doc.datajud_api_key.strip()
	except Exception:
		pass
	return None


def cnj_to_tribunal_alias(numero_20_digitos: str) -> Optional[str]:
	"""
	Retorna o alias do índice Datajud a partir do número CNJ (20 dígitos).
	Ex.: '000000000200251026' -> 'api_publica_trt2' (segmento 5, TR 02).
	"""
	numero_20_digitos = _normalize_cnj(numero_20_digitos)
	if len(numero_20_digitos) != 20:
		return None
	# Posições 0-based: 13 = J (segmento), 14:16 = TR (2 dígitos)
	try:
		segmento = int(numero_20_digitos[13])
		tr = int(numero_20_digitos[14:16])
	except (ValueError, IndexError):
		return None
	alias = SEGMENT_TR_TO_ALIAS.get((segmento, tr))
	if alias:
		return f"api_publica_{alias}"
	# Fallback: alguns tribunais podem usar segmento 1/2 para STF/CNJ
	if segmento == 1:
		return "api_publica_stf"
	if segmento == 2:
		return "api_publica_cnj"
	return None


def buscar_processo(numero_cnj: str) -> Optional[dict]:
	"""
	Consulta a API Datajud pelo número único do processo (20 dígitos).
	Retorna o _source do primeiro hit ou None se não encontrar / erro.
	"""
	if not requests:
		logger.warning("Biblioteca 'requests' não instalada; integração Datajud indisponível.")
		return None

	numero = _normalize_cnj(numero_cnj)
	if len(numero) != 20:
		logger.warning("Número CNJ inválido (deve ter 20 dígitos): %s", numero_cnj[:10] + "...")
		return None

	alias = cnj_to_tribunal_alias(numero)
	if not alias:
		logger.warning("Tribunal não mapeado para o número CNJ (segmento/TR): %s", numero)
		return None

	api_key = get_api_key()
	if not api_key:
		logger.warning("Chave API Datajud não configurada (datajud_api_key).")
		return None

	if not frappe.conf.get("contencioso_integracao_ativa"):
		logger.info("Integração contencioso desativada (contencioso_integracao_ativa).")
		return None

	url = f"{BASE_URL.rstrip('/')}/{alias}/_search"
	headers = {"Authorization": f"APIKey {api_key}", "Content-Type": "application/json"}
	payload = {"query": {"term": {"numeroProcesso": numero}}, "size": 1}

	try:
		resp = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
	except requests.RequestException as e:
		logger.exception("Erro de rede ao consultar Datajud: %s", str(e))
		return None

	if resp.status_code == 401:
		logger.warning("Datajud: credencial inválida (401).")
		return None
	if resp.status_code == 404:
		logger.info("Datajud: processo não encontrado ou índice inexistente.")
		return None
	if resp.status_code != 200:
		logger.warning("Datajud: resposta HTTP %s", resp.status_code)
		return None

	try:
		data = resp.json()
		hits = (data.get("hits") or {}).get("hits") or []
		if not hits:
			return None
		return hits[0].get("_source")
	except Exception as e:
		logger.exception("Erro ao interpretar resposta Datajud: %s", str(e))
		return None


def _nivel_sigilo_datajud_to_doc(nivel: Optional[int]) -> str:
	"""Mapeia nivelSigilo (0-5) da API para opções do DocType: Publico, Restrito, Sigiloso."""
	if nivel is None:
		return "Publico"
	if nivel == 0:
		return "Publico"
	if nivel == 1:
		return "Restrito"
	return "Sigiloso"


def _parse_data_ajuizamento(value) -> Optional[str]:
	"""Converte dataAjuizamento (datetime/string) para string Date YYYY-MM-DD."""
	if value is None:
		return None
	s = str(value).strip()
	if not s:
		return None
	# Pode vir como "2025-01-15T00:00:00" ou "20250115"
	if "T" in s:
		s = s.split("T")[0]
	if len(s) >= 10 and s[4] == "-":
		return s[:10]
	if len(s) >= 8 and s.isdigit():
		return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
	return None


def _parse_datetime(value) -> Optional[str]:
	"""Converte dataHora da API para string datetime aceita pelo Frappe."""
	if value is None:
		return None
	s = str(value).strip()
	if not s:
		return None
	# ISO ou "20250115120000"
	if "T" in s:
		return s[:19].replace("T", " ")
	if len(s) >= 14 and s.isdigit():
		return f"{s[:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}:{s[10:12]}:{s[12:14]}"
	if len(s) >= 10:
		return s[:19] if " " in s else s + " 00:00:00"
	return None


def mapear_resposta_para_form(hit: dict, numero_cnj_20: str) -> dict:
	"""
	Mapeia o _source da API Datajud (glossário) para payload do formulário Processo Judicial.
	Retorna dict com chaves: processo (campos do DocType), cj_eventos (lista de dicts), cj_integracoes (lista com 1 item).
	"""
	processo = {}
	# Capa
	processo["cj_numero_cnj"] = numero_cnj_20
	if hit.get("dataAjuizamento") is not None:
		processo["cj_data_distribuicao"] = _parse_data_ajuizamento(hit["dataAjuizamento"])
	if hit.get("tribunal"):
		processo["cj_tribunal"] = str(hit["tribunal"]).strip()
	classe = hit.get("classe") or {}
	if isinstance(classe, dict) and classe.get("nome"):
		processo["cj_classe"] = str(classe["nome"]).strip()
	assuntos = hit.get("assuntos") or []
	if isinstance(assuntos, list):
		nomes = []
		for a in assuntos:
			if isinstance(a, dict) and a.get("nome"):
				nomes.append(str(a["nome"]).strip())
		if nomes:
			processo["cj_assuntos"] = "\n".join(nomes)
	orgao = hit.get("orgaoJulgador") or {}
	if isinstance(orgao, dict) and orgao.get("nome"):
		processo["cj_vara_foro"] = str(orgao["nome"]).strip()
	if hit.get("nivelSigilo") is not None:
		processo["cj_nivel_sigilo"] = _nivel_sigilo_datajud_to_doc(hit.get("nivelSigilo"))
	if hit.get("grau"):
		# Opcional: inferir cj_sistema_justica se quiser (JE, G1, etc.)
		pass

	# Movimentações -> CJ Evento
	eventos = []
	movimentos = hit.get("movimentos") or []
	hit_id = str(hit.get("id") or "")
	for idx, mov in enumerate(movimentos):
		if not isinstance(mov, dict):
			continue
		data_hora = _parse_datetime(mov.get("dataHora"))
		nome = (mov.get("nome") or "").strip() or "Movimento"
		# Idempotência: id estável
		cj_id_externo = f"{hit_id}_{idx}" if hit_id else f"mov_{idx}"
		eventos.append({
			"cj_data_hora": data_hora or frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M:%S"),
			"cj_origem": "Integração",
			"cj_tipo_evento": "Movimento",
			"cj_resumo": nome[:140],
			"cj_detalhes": _detalhes_movimento(mov),
			"cj_id_externo": cj_id_externo,
		})

	# CJ Integracao (1 linha)
	integracao = {
		"cj_provedor": "DataJud",
		"cj_chave_externa": hit_id or numero_cnj_20,
		"cj_ultima_sync_em": frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M:%S"),
		"cj_status_sync": "OK",
		"cj_log_sync": "Consulta por número CNJ",
	}

	return {
		"processo": processo,
		"cj_eventos": eventos,
		"cj_integracoes": [integracao],
	}


def _detalhes_movimento(mov: dict) -> str:
	"""Monta texto de detalhes a partir de complementos e orgao do movimento."""
	partes = []
	comp = mov.get("complementosTabelados") or []
	if isinstance(comp, list):
		for c in comp:
			if isinstance(c, dict) and c.get("nome"):
				partes.append(str(c["nome"]).strip())
	orgao = mov.get("orgaoJulgador") or {}
	if isinstance(orgao, dict) and orgao.get("nomeOrgao"):
		partes.append(f"Órgão: {orgao['nomeOrgao']}")
	if not partes:
		return ""
	return "\n".join(partes)


@frappe.whitelist()
def buscar_processo_para_form(numero_cnj: str) -> dict:
	"""
	Chamada whitelisted para o formulário: busca processo na API Datajud e retorna
	payload para preencher Processo Judicial + cj_eventos + cj_integracoes.
	Retorno: { "ok": true, "processo": {}, "cj_eventos": [], "cj_integracoes": [] } ou { "ok": false, "error": "..." }.
	"""
	numero = _normalize_cnj(numero_cnj or "")
	if len(numero) != 20:
		return {"ok": False, "error": "Número CNJ deve conter exatamente 20 dígitos."}

	hit = buscar_processo(numero)
	if not hit:
		return {"ok": False, "error": "Processo não encontrado no Datajud ou integração indisponível."}

	try:
		payload = mapear_resposta_para_form(hit, numero)
		return {
			"ok": True,
			"processo": payload["processo"],
			"cj_eventos": payload["cj_eventos"],
			"cj_integracoes": payload["cj_integracoes"],
		}
	except Exception as e:
		logger.exception("Erro ao mapear resposta Datajud: %s", str(e))
		return {"ok": False, "error": str(e)}
