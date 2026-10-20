"""Roteamento de envios entre instâncias da Evolution API.

A instância principal (`instance_name`) mais as linhas ativas de `instancias` formam o conjunto. Com uma só
instância nada muda (sem consulta extra). Com várias, cada envio vai para a conectada de menor carga do dia
(`carga / peso`), respeitando `limite_diario`, e o mesmo destinatário volta à mesma instância (afinidade) para
não dividir a conversa entre dois números.

Contadores e afinidade ficam no cache do Redis: são heurísticas de balanceamento, não registro contábil.
"""

import hashlib

import frappe
from frappe.utils import today

PREFIXO_CARGA = "evolution_carga"
PREFIXO_AFINIDADE = "evolution_afinidade"
PREFIXO_ESTADO = "evolution_estado"
VALIDADE_ESTADO_S = 30
VALIDADE_AFINIDADE_S = 14 * 24 * 3600
VALIDADE_CARGA_S = 2 * 24 * 3600


class SemInstanciaDisponivel(Exception):
	"""Nenhuma instância elegível (todas desconectadas ou no limite diário)."""


def instancias(settings) -> list[dict]:
	"""`[{"nome", "peso", "limite"}]`: a principal primeiro, depois as adicionais ativas."""
	lista = [{"nome": settings.instance_name, "peso": 1, "limite": 0}]
	for linha in getattr(settings, "instancias", None) or []:
		nome = (linha.get("instance_name") or "").strip()
		if nome and linha.get("ativo") and nome not in {i["nome"] for i in lista}:
			lista.append({"nome": nome, "peso": max(linha.get("peso") or 1, 1), "limite": linha.get("limite_diario") or 0})
	return lista


def nomes(settings) -> list[str]:
	return [i["nome"] for i in instancias(settings)]


def _chave_carga(nome):
	return f"{PREFIXO_CARGA}:{nome}:{today()}"


def _carga(nome) -> int:
	return int(frappe.cache.get_value(_chave_carga(nome), expires=True) or 0)


def _conectada(nome, estado) -> bool:
	chave = f"{PREFIXO_ESTADO}:{nome}"
	conhecido = frappe.cache.get_value(chave, expires=True)
	if conhecido is not None:
		return bool(conhecido)
	try:
		resultado = bool(estado(nome))
	except Exception:
		resultado = False
	frappe.cache.set_value(chave, int(resultado), expires_in_sec=VALIDADE_ESTADO_S)
	return resultado


def estado_padrao(nome) -> bool:
	"""Consulta `connectionState` da instância pela API de configuração."""
	from integracoes_customizadas.whatsapp.api import evolution_request, instance_path

	dados = evolution_request("GET", instance_path("connectionState", nome))
	return ((dados or {}).get("instance") or {}).get("state") == "open"


def escolher_instancia(numero=None, *, preferida=None, excluir=(), estado=estado_padrao) -> str:
	"""Nome da instância que deve enviar para `numero`.

	`preferida` (ex.: a que já enviou este registro) tem prioridade se ainda elegível; `estado(nome)` diz se
	a instância está conectada. Reserva a carga no momento da escolha, o que distribui também workers concorrentes.
	"""
	from integracoes_customizadas.whatsapp.api import get_settings

	todas = [i for i in instancias(get_settings()) if i["nome"] not in excluir]
	if not todas:
		raise SemInstanciaDisponivel
	if len(todas) == 1 and not excluir:
		return todas[0]["nome"]

	elegiveis = [
		i for i in todas if (not i["limite"] or _carga(i["nome"]) < i["limite"]) and _conectada(i["nome"], estado)
	]
	if not elegiveis:
		raise SemInstanciaDisponivel

	nomes_elegiveis = {i["nome"] for i in elegiveis}
	chave_afinidade = (
		f"{PREFIXO_AFINIDADE}:{hashlib.sha1(str(numero).encode()).hexdigest()}" if numero else None  # sem número no Redis
	)
	anterior = preferida or (chave_afinidade and frappe.cache.get_value(chave_afinidade, expires=True))
	if anterior in nomes_elegiveis:
		escolhida = anterior
	else:
		escolhida = min(elegiveis, key=lambda i: _carga(i["nome"]) / i["peso"])["nome"]

	frappe.cache.set_value(_chave_carga(escolhida), _carga(escolhida) + 1, expires_in_sec=VALIDADE_CARGA_S)
	if chave_afinidade:
		frappe.cache.set_value(chave_afinidade, escolhida, expires_in_sec=VALIDADE_AFINIDADE_S)
	return escolhida


def multiplas(settings) -> bool:
	return len(instancias(settings)) > 1
