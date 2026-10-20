"""Roteador de variantes de mensagem do WhatsApp.

Escolhe uma entre várias redações da mesma mensagem para que envios em série não repitam o mesmo texto.
Nunca repete as últimas variantes usadas na mesma `chave` nem a última enviada ao mesmo destinatário;
o destinatário só entra no cache como hash.
"""

import hashlib
import random

import frappe

HISTORICO_GLOBAL = 3
TTL_S = 24 * 3600


def _chave_global(chave) -> str:
	return f"whatsapp_variantes:{chave}"


def _chave_destino(chave, destino) -> str:
	digest = hashlib.sha256(f"{chave}:{destino}".encode()).hexdigest()[:24]
	return f"whatsapp_variante_destino:{digest}"


def variar_ativo() -> bool:
	"""Interruptor global em `Configuracoes WhatsApp` (ausente = ligado)."""
	valor = frappe.db.get_single_value("Configuracoes WhatsApp", "variar_mensagens")
	return valor is None or bool(int(valor))


def _id(item, indice) -> str:
	return str(item.get("name") or item.get("id") or indice)


def escolher(variantes, *, chave, destino=None):
	"""→ (item, id) sorteado entre as variantes ativas, ou (None, None) se não houver nenhuma.

	`variantes`: lista de objetos/dicts com `mensagem`, `peso` (padrão 1) e `ativo` (padrão 1).
	Se as exclusões esgotarem as opções, relaxam primeiro a do destinatário e depois a global.
	"""
	ativas = [(_id(v, i), v) for i, v in enumerate(variantes or []) if v.get("ativo", 1)]
	if not ativas:
		return None, None
	recentes = frappe.cache.get_value(_chave_global(chave), expires=True) or []
	ultima_destino = frappe.cache.get_value(_chave_destino(chave, destino), expires=True) if destino else None
	limite = min(HISTORICO_GLOBAL, len(ativas) - 1)
	excluir_global = set(recentes[-limite:]) if limite > 0 else set()
	excluir_destino = {ultima_destino} if ultima_destino else set()

	candidatas = [a for a in ativas if a[0] not in excluir_global | excluir_destino]
	if not candidatas:
		candidatas = [a for a in ativas if a[0] not in excluir_global]
	if not candidatas:
		candidatas = ativas
	escolhida = random.choices(candidatas, weights=[max(int(v.get("peso") or 1), 1) for _i, v in candidatas])[0]

	identificador = escolhida[0]
	frappe.cache.set_value(
		_chave_global(chave), [*recentes, identificador][-HISTORICO_GLOBAL:], expires_in_sec=TTL_S
	)
	if destino:
		frappe.cache.set_value(_chave_destino(chave, destino), identificador, expires_in_sec=TTL_S)
	return escolhida[1], identificador


def sorteio(*opcoes) -> str:
	"""Função Jinja `sorteio("Oi","Olá","E aí")` para variar trechos dentro de um mesmo texto."""
	return str(random.choice(opcoes)) if opcoes else ""
