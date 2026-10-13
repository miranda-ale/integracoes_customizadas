"""Conector estável da Evolution API v2 (modo Baileys) para outros apps.

API pública: `estado_conexao`, `verificar_numero`, `enviar_texto` e `normalizar_numero_br`.
O modo Baileys não é oficial: o canal é "melhor esforço" e pode cair sem aviso, então toda falha
vira uma exceção própria que o chamador trata como caso normal (ex.: fallback para outro canal).

Não há retry em envio (evita mensagem/OTP duplicado); só GET idempotente tenta uma segunda vez.
"""

import random
import re
import time
from urllib.parse import quote

import frappe
import requests
from frappe import _

CHAVE_ULTIMO_ENVIO = "evolution_ultimo_envio"

# DDDs válidos no Brasil (Anatel).
DDDS = frozenset(
	"11 12 13 14 15 16 17 18 19 21 22 24 27 28 31 32 33 34 35 37 38 41 42 43 44 45 46 47 48 49 "
	"51 53 54 55 61 62 63 64 65 66 67 68 69 71 73 74 75 77 79 81 82 83 84 85 86 87 88 89 91 92 93 94 95 96 97 98 99".split()
)


class EvolutionIndisponivel(Exception):
	"""Servidor fora do ar, sem rede, instância desconectada ou conector desativado/não configurado."""


class NumeroInvalido(Exception):
	"""Número malformado ou inexistente no WhatsApp."""


class EnvioRejeitado(Exception):
	"""O servidor respondeu e recusou a requisição (4xx), ex.: chave inválida ou instância inexistente."""


def normalizar_numero_br(bruto) -> str | None:
	"""Devolve `55` + DDD + número, ou None. Aceita máscara, `+55` e zeros de operadora à esquerda."""
	digitos = re.sub(r"\D", "", str(bruto or "")).lstrip("0")
	# 10-11 dígitos: nacional (DDD + número). 12-13 começando em 55: já com o código do país.
	if len(digitos) in (12, 13) and digitos.startswith("55"):
		nacional = digitos[2:]
	elif len(digitos) in (10, 11):
		nacional = digitos
	else:
		return None
	ddd, assinante = nacional[:2], nacional[2:]
	if ddd not in DDDS:
		return None
	if len(assinante) == 9 and assinante[0] != "9":
		return None
	if len(assinante) == 8 and assinante[0] == "0":
		return None
	return "55" + nacional


def mascarar(numero) -> str:
	"""Só os 4 últimos dígitos entram em log."""
	return "***" + re.sub(r"\D", "", str(numero or ""))[-4:]


def _settings():
	from integracoes_customizadas.whatsapp.api import get_settings

	try:
		return get_settings()
	except frappe.ValidationError as exc:  # não configurado ou desativado
		raise EvolutionIndisponivel(_("Conector WhatsApp não configurado ou desativado.")) from exc


def _registrar_erro(titulo, exc, numero=None):
	"""Nunca registra a chave, o texto da mensagem nem o número completo."""
	frappe.log_error(
		title=titulo,
		message=f"{type(exc).__name__}: {exc}" + (f"\nNúmero: {mascarar(numero)}" if numero else ""),
	)


def _requisicao(metodo, caminho, *, json=None, repetir=False):
	settings = _settings()
	instancia = quote(settings.instance_name, safe="")
	url = f"{settings.server_url.rstrip('/')}/{caminho.format(instancia=instancia).lstrip('/')}"
	timeout = (settings.get("timeout_conexao_s") or 5, settings.get("timeout_leitura_s") or 15)
	tentativas = 2 if repetir and metodo == "GET" else 1
	ultimo = None
	for _tentativa in range(tentativas):
		try:
			resposta = requests.request(
				metodo,
				url,
				headers={"apikey": settings.get_password("api_key"), "Content-Type": "application/json"},
				json=json,
				timeout=timeout,
			)
		except requests.RequestException as exc:  # timeout, DNS, conexão recusada
			ultimo = EvolutionIndisponivel(_("Não foi possível comunicar com a Evolution API."))
			ultimo.__cause__ = exc
			continue
		if resposta.status_code >= 500:
			ultimo = EvolutionIndisponivel(
				_("Evolution API indisponível (HTTP {0}).").format(resposta.status_code)
			)
			continue
		if resposta.status_code in (401, 403):
			raise EnvioRejeitado(
				_("Chave da Evolution API recusada (HTTP {0}).").format(resposta.status_code)
			)
		if resposta.status_code == 404:
			raise EnvioRejeitado(_("Instância do WhatsApp não encontrada (HTTP 404)."))
		if resposta.status_code >= 400:
			raise EnvioRejeitado(
				_("Evolution API recusou a requisição (HTTP {0}).").format(resposta.status_code)
			)
		try:
			return resposta.json()
		except ValueError as exc:
			raise EvolutionIndisponivel(_("Resposta inválida da Evolution API.")) from exc
	raise ultimo


def estado_conexao() -> dict:
	"""`{"conectado": bool, "estado": str}`; falha de comunicação conta como desconectado."""
	try:
		dados = _requisicao("GET", "instance/connectionState/{instancia}", repetir=True)
	except (EvolutionIndisponivel, EnvioRejeitado) as exc:
		_registrar_erro("WhatsApp: falha ao consultar a conexão", exc)
		return {"conectado": False, "estado": "indisponivel"}
	estado = ((dados or {}).get("instance") or {}).get("state") or "desconhecido"
	return {"conectado": estado == "open", "estado": estado}


def verificar_numero(numero) -> dict:
	"""Confirma que o número existe no WhatsApp.

	O número/JID devolvido é o canônico (o WhatsApp pode omitir o nono dígito de celulares antigos).
	"""
	normalizado = normalizar_numero_br(numero)
	if not normalizado:
		raise NumeroInvalido(_("Número de telefone inválido."))
	dados = _requisicao(
		"POST", "chat/whatsappNumbers/{instancia}", json={"numbers": [normalizado]}, repetir=False
	)
	item = next((i for i in (dados if isinstance(dados, list) else []) if isinstance(i, dict)), {})
	if not item.get("exists"):
		return {"existe": False, "numero": None, "jid": None}
	jid = item.get("jid")
	return {
		"existe": True,
		"numero": item.get("number") or (jid or "").split("@")[0] or normalizado,
		"jid": jid,
	}


def _aguardar_espaco(settings):
	"""Intervalo aleatório desde o último envio (anti-ban). Reserva o horário antes de dormir para que
	workers concorrentes não disparem juntos."""
	minimo, maximo = settings.get("delay_min_s") or 2, settings.get("delay_max_s") or 6
	agora = time.time()
	ultimo = frappe.cache.get_value(CHAVE_ULTIMO_ENVIO) or 0
	horario = max(agora, ultimo + random.uniform(min(minimo, maximo), max(minimo, maximo)))
	frappe.cache.set_value(CHAVE_ULTIMO_ENVIO, horario, expires_in_sec=3600)
	if horario > agora:
		time.sleep(horario - agora)


def enviar_texto(numero, texto, *, prioridade="normal") -> dict:
	"""Envia texto. `prioridade="alta"` (OTP) não aguarda o espaçamento.

	Sucesso → `{"ok": True, "message_id", "status", "erro": None}`. Falhas levantam `NumeroInvalido`,
	`EvolutionIndisponivel` ou `EnvioRejeitado` (já registradas em log sem chave, texto ou número completo).
	"""
	settings = _settings()
	destino = normalizar_numero_br(numero)
	if not destino:
		raise NumeroInvalido(_("Número de telefone inválido."))
	try:
		if settings.get("verificar_numero_antes"):
			verificado = verificar_numero(destino)
			if not verificado["existe"]:
				raise NumeroInvalido(_("O número não possui WhatsApp."))
			destino = verificado["numero"]
		if prioridade != "alta":
			_aguardar_espaco(settings)
		else:
			frappe.cache.set_value(CHAVE_ULTIMO_ENVIO, time.time(), expires_in_sec=3600)
		dados = _requisicao("POST", "message/sendText/{instancia}", json={"number": destino, "text": texto})
	except (EvolutionIndisponivel, EnvioRejeitado, NumeroInvalido) as exc:
		_registrar_erro("WhatsApp: falha no envio", exc, destino)
		raise
	dados = dados if isinstance(dados, dict) else {}
	return {
		"ok": True,
		"message_id": (dados.get("key") or {}).get("id"),
		"status": dados.get("status") or "PENDING",
		"erro": None,
	}
