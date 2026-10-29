# Copyright (c) 2026, BHCL and contributors
# For license information, please see license.txt
"""Layout enxuto dos workspaces Compras (Buying) e Estoque (Stock), reaplicado a cada migrate.

O layout é dono destes dois workspaces: atalhos na ordem do fluxo de compras e poucos cards, só com o que é usado
no site (DocTypes com registros). Ajustes feitos pela tela nesses dois workspaces são sobrescritos no próximo
migrate; para mudar, altere LAYOUTS. Só salva quando algo mudou, para não mexer no `modified` a cada migrate.
"""

import hashlib
import json

import frappe

# Atalho: (rótulo, tipo, alvo, stats_filter ou None, formato do contador ou None, cor)
# Card: (rótulo, [(rótulo, tipo, alvo)])

# Each workspace opens with a card of its own flow, numbered: in a usability test people did not notice the shortcut
# tiles, only the cards. Each user only sees the links they can read (e.g. Stock User does not see the invoice steps).
CARD_FLUXO_COMPRAS = (
	"Fluxo de compras",
	[
		("1. Solicitação de Compras", "DocType", "Material Request"),
		("2. Pedido de Cotação", "DocType", "Request for Quotation"),
		("3. Cotação do Fornecedor", "DocType", "Supplier Quotation"),
		("4. Ordem de Compra", "DocType", "Purchase Order"),
		("5. Pedidos a Receber", "Report", "Pedidos a Receber"),
		("6. Recebimento de Compra", "DocType", "Purchase Receipt"),
		("7. Recebidos a Faturar", "Report", "Recebidos a Faturar"),
		("8. Nota Fiscal de Compra", "DocType", "Purchase Invoice"),
	],
)

# The unit's cycle: receive what was ordered, move it, check the balance and ask for replenishment.
CARD_FLUXO_ESTOQUE = (
	"Fluxo do recebimento e estoque",
	[
		("1. Pedidos a Receber", "Report", "Pedidos a Receber"),
		("2. Recebimento de Compra", "DocType", "Purchase Receipt"),
		("3. Movimento de Estoque", "DocType", "Stock Entry"),
		("4. Saldo de Estoque", "Report", "Stock Balance"),
		("5. Solicitação de Compras (reposição)", "DocType", "Material Request"),
	],
)

LAYOUTS = {
	"Buying": {
		"header": "Fluxo de compras",
		"shortcuts": [
			(
				"Solicitação de Compras",
				"DocType",
				"Material Request",
				{"status": "Pending"},
				"{} pendentes",
				"Yellow",
			),
			("Pedido de Cotação", "DocType", "Request for Quotation", None, None, "Grey"),
			("Cotação do Fornecedor", "DocType", "Supplier Quotation", None, None, "Grey"),
			(
				"Ordem de Compra",
				"DocType",
				"Purchase Order",
				{"status": ["in", ["To Receive and Bill", "To Receive"]]},
				"{} a receber",
				"Yellow",
			),
			("Pedidos a Receber", "Report", "Pedidos a Receber", None, None, "Blue"),
			(
				"Recebimento de Compra",
				"DocType",
				"Purchase Receipt",
				{"docstatus": 0},
				"{} em rascunho",
				"Grey",
			),
			("Recebidos a Faturar", "Report", "Recebidos a Faturar", None, None, "Blue"),
			(
				"Nota Fiscal de Compra",
				"DocType",
				"Purchase Invoice",
				{"docstatus": 0},
				"{} em rascunho",
				"Grey",
			),
		],
		"cards": [
			CARD_FLUXO_COMPRAS,
			(
				"Bionexo",
				[
					("Importação do PDF Bionexo", "DocType", "Importacao Bionexo"),
					("Mapa de Preços", "Report", "Mapa de Precos RFQ"),
				],
			),
			(
				"Cadastros",
				[
					("Fornecedor", "DocType", "Supplier"),
					("Item", "DocType", "Item"),
					("Documentos do Fornecedor", "DocType", "CLM Supplier Document"),
					("Lista de Preços", "DocType", "Price List"),
				],
			),
			(
				"Relatórios",
				[
					("Análise de pedidos de compra", "Report", "Purchase Order Analysis"),
					("Itens a pedir e receber", "Report", "Requested Items to Order and Receive"),
					("Rastreador de compras", "Report", "Procurement Tracker"),
					("Histórico de compras por item", "Report", "Item-wise Purchase History"),
					("Comparação de cotações", "Report", "Supplier Quotation Comparison"),
					("Documentos de fornecedor a vencer", "Report", "CLM Documentos de Fornecedor a Vencer"),
				],
			),
			(
				"Configurações",
				[
					("Configurações de Compras", "DocType", "Buying Settings"),
					("Modelo de impostos sobre compras", "DocType", "Purchase Taxes and Charges Template"),
					("Termos e Condições", "DocType", "Terms and Conditions"),
				],
			),
		],
	},
	"Stock": {
		"header": "Recebimento e estoque",
		"shortcuts": [
			("Pedidos a Receber", "Report", "Pedidos a Receber", None, None, "Blue"),
			(
				"Recebimento de Compra",
				"DocType",
				"Purchase Receipt",
				{"docstatus": 0},
				"{} em rascunho",
				"Grey",
			),
			("Movimento de Estoque", "DocType", "Stock Entry", None, None, "Grey"),
			("Saldo de Estoque", "Report", "Stock Balance", None, None, "Grey"),
			(
				"Solicitação de Compras",
				"DocType",
				"Material Request",
				{"status": "Pending"},
				"{} pendentes",
				"Yellow",
			),
			("Item", "DocType", "Item", None, None, "Grey"),
		],
		"cards": [
			CARD_FLUXO_ESTOQUE,
			(
				"Consultas",
				[
					("Saldo de estoque", "Report", "Stock Balance"),
					("Razão de estoque", "Report", "Stock Ledger"),
					("Consulta rápida de estoque", "DocType", "Quick Stock Balance"),
					("Estoque projetado", "Report", "Stock Projected Qty"),
					("Validade dos lotes", "Report", "Batch Item Expiry Status"),
				],
			),
			(
				"Cadastros",
				[
					("Item", "DocType", "Item"),
				],
			),
			(
				"Configurações",
				[
					("Configurações de Estoque", "DocType", "Stock Settings"),
					("Ajuste de estoque (inventário)", "DocType", "Stock Reconciliation"),
					("Fator de conversão de UM", "DocType", "UOM Conversion Factor"),
					("Atributos do Item", "DocType", "Item Attribute"),
					("Configurações de variante", "DocType", "Item Variant Settings"),
				],
			),
		],
	},
}


def _existe(tipo, alvo):
	return bool(frappe.db.exists(tipo, alvo))


def _ref_doctype(tipo, alvo):
	return frappe.db.get_value("Report", alvo, "ref_doctype") if tipo == "Report" else None


def _bloco(tipo, data):
	"""Bloco do editor com id estável (derivado do conteúdo), para a comparação não mudar a cada execução."""
	chave = json.dumps([tipo, data], sort_keys=True, ensure_ascii=False)
	return {"id": hashlib.md5(chave.encode()).hexdigest()[:10], "type": tipo, "data": data}


def montar(nome):
	"""(links, shortcuts, content) desejados; alvos inexistentes são ignorados (ex.: relatório removido)."""
	layout = LAYOUTS[nome]
	atalhos = [a for a in layout["shortcuts"] if _existe(a[1], a[2])]
	shortcuts = [
		{
			"label": rotulo,
			"type": tipo,
			"link_to": alvo,
			"doc_view": "List" if tipo == "DocType" else "",
			"report_ref_doctype": _ref_doctype(tipo, alvo),
			"stats_filter": json.dumps(filtro) if filtro else None,
			"format": formato,
			"color": cor,
		}
		for rotulo, tipo, alvo, filtro, formato, cor in atalhos
	]
	links, cards = [], []
	for card, itens in layout["cards"]:
		itens = [i for i in itens if _existe(i[1], i[2])]
		if not itens:
			continue
		cards.append(card)
		links.append({"type": "Card Break", "label": card, "link_count": len(itens), "hidden": 0})
		links += [
			{
				"type": "Link",
				"label": rotulo,
				"link_type": tipo,
				"link_to": alvo,
				"is_query_report": 1 if tipo == "Report" else 0,
				"report_ref_doctype": _ref_doctype(tipo, alvo),
				"hidden": 0,
			}
			for rotulo, tipo, alvo in itens
		]
	content = [_bloco("header", {"text": f'<span class="h4"><b>{layout["header"]}</b></span>', "col": 12})]
	content += [_bloco("shortcut", {"shortcut_name": s["label"], "col": 3}) for s in shortcuts]
	content += [_bloco("spacer", {"col": 12})]
	content += [_bloco("card", {"card_name": c, "col": 4}) for c in cards]
	return links, shortcuts, content


CAMPOS_LINK = ("type", "label", "link_type", "link_to", "is_query_report", "report_ref_doctype")
CAMPOS_ATALHO = (
	"label",
	"type",
	"link_to",
	"doc_view",
	"report_ref_doctype",
	"stats_filter",
	"format",
	"color",
)


def _assinatura(links, shortcuts, content, extras):
	"""Forma comparável do workspace ("" / 0 / None equivalem, como o banco os devolve)."""
	# Card Break only matters by label (Frappe fills the link_type default on its rows).
	return (
		[
			{c: l.get(c) or None for c in (CAMPOS_LINK if l.get("type") == "Link" else ("type", "label"))}
			for l in links
		],
		[{c: s.get(c) or None for c in CAMPOS_ATALHO} for s in shortcuts],
		content,
		extras,
	)


def aplicar_layout(nome):
	if not frappe.db.exists("Workspace", nome):
		return False
	links, shortcuts, content = montar(nome)
	ws = frappe.get_doc("Workspace", nome)
	atual = _assinatura(
		[l.as_dict() for l in ws.links],
		[s.as_dict() for s in ws.shortcuts],
		json.loads(ws.content or "[]"),
		len(ws.number_cards) + len(ws.charts),
	)
	if atual == _assinatura(links, shortcuts, content, 0):
		return False
	ws.set("links", links)
	ws.set("shortcuts", shortcuts)
	ws.set("number_cards", [])
	ws.set("charts", [])
	ws.content = json.dumps(content, ensure_ascii=False)
	ws.flags.ignore_permissions = True
	ws.flags.ignore_links = True
	ws.save()
	return True


def aplicar_layouts():
	alterados = [nome for nome in LAYOUTS if aplicar_layout(nome)]
	if alterados:
		frappe.clear_cache()
	return alterados
