# Copyright (c) 2026, BHCL and contributors
# For license information, please see license.txt
"""Atalhos de Workspace para os DocTypes deste app (idempotente, roda a cada migrate).

Política de acesso (`acesso_doctypes.py`): todo DocType do app precisa de um local de acesso. Aqui cada DocType
ganha um link, num card próprio, no primeiro workspace existente da lista de candidatos. Só acrescenta o que falta:
um DocType que já tem link ou atalho em qualquer workspace público fica como está, e nada é removido nem
reordenado. Workspaces inexistentes no site são ignorados. A visibilidade continua sendo do Frappe: o link só
aparece a quem pode ler o DocType.
"""

import json

import frappe

from integracoes_customizadas.politicas.acesso_doctypes import _workspaces_publicos

# (card, [(rótulo, DocType)], workspaces candidatos em ordem de preferência)
ATALHOS = (
	(
		"WhatsApp",
		[
			("Configurações do WhatsApp", "Configuracoes WhatsApp"),
			("Envios de WhatsApp", "Envio WhatsApp"),
			("Modelos de WhatsApp", "Modelo WhatsApp"),
		],
		("Integrations",),
	),
	("Cadastros do RH", [("Tipo de Deficiência", "Tipo de Deficiencia")], ("HR",)),
	(
		"Provas",
		[
			("Disciplinas", "Disciplina"),
			("Editais", "Edital"),
			("Provas", "Prova"),
			("Questões", "Questao"),
		],
		("Recruitment", "HR"),
	),
	("Configurações", [("Log de Sincronização DataJud", "DataJud Sync Log")], ("Jurídico",)),
)


def _doctypes_ja_acessiveis():
	"""DocTypes com link ou atalho em algum workspace público e visível."""
	return set().union(*(alvos for _, alvos in _workspaces_publicos().values()))


def _acrescentar(nome_ws, card, itens):
	"""Acrescenta os links ausentes ao card (criado no fim do workspace se ainda não existir)."""
	ws = frappe.get_doc("Workspace", nome_ws)
	links = [l.as_dict() for l in ws.links]
	novos = [
		{"type": "Link", "label": r, "link_type": "DocType", "link_to": d, "hidden": 0} for r, d in itens
	]
	posicao = next((i for i, l in enumerate(links) if l.type == "Card Break" and l.label == card), None)
	if posicao is None:
		links.append({"type": "Card Break", "label": card, "link_count": len(novos), "hidden": 0})
		links += novos
		inserido_em_card_novo = True
	else:
		fim = posicao + 1
		while fim < len(links) and links[fim].type != "Card Break":
			fim += 1
		links[fim:fim] = novos
		links[posicao]["link_count"] = (links[posicao].get("link_count") or 0) + len(novos)
		inserido_em_card_novo = False
	ws.set("links", links)
	for i, l in enumerate(ws.links, start=1):
		l.idx = i
	if inserido_em_card_novo:
		try:
			blocos = json.loads(ws.content or "[]")
		except ValueError:
			blocos = []
		if not any((b.get("data") or {}).get("card_name") == card for b in blocos):
			blocos.append(
				{"id": frappe.generate_hash(length=10), "type": "card", "data": {"card_name": card, "col": 4}}
			)
			ws.content = json.dumps(blocos, ensure_ascii=False)
	ws.flags.ignore_permissions = True
	ws.flags.ignore_links = True
	ws.save()


def garantir_atalhos():
	"""Devolve {workspace: [DocTypes acrescentados]}."""
	acrescentados = {}
	acessiveis = _doctypes_ja_acessiveis()
	for card, itens, candidatos in ATALHOS:
		destino = next((w for w in candidatos if frappe.db.exists("Workspace", w)), None)
		if not destino:
			continue
		faltantes = [(r, d) for r, d in itens if frappe.db.exists("DocType", d) and d not in acessiveis]
		if not faltantes:
			continue
		_acrescentar(destino, card, faltantes)
		acrescentados.setdefault(destino, []).extend(d for _, d in faltantes)
		acessiveis.update(d for _, d in faltantes)
	if acrescentados:
		frappe.clear_cache()
	return acrescentados
