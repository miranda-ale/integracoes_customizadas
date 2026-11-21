"""Card "Bionexo" no workspace Buying com o atalho da Importacao Bionexo (idempotente)."""

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

WORKSPACE = "Buying"
CARD_LABEL = "Bionexo"
LINKS = [("Importacao Bionexo", "Importação do PDF Bionexo")]


def ensure_buying_card():
	if not frappe.db.exists("Workspace", WORKSPACE):
		return
	desejados = [(d, r) for d, r in LINKS if frappe.db.exists("DocType", d)]
	if not desejados:
		return
	ws = frappe.get_doc("Workspace", WORKSPACE)
	existentes = {l.link_to for l in ws.links if l.type == "Link"}
	faltantes = [(d, r) for d, r in desejados if d not in existentes]
	alterado = False
	if faltantes:
		# O desk agrupa os links pela ordem de idx; o Buying tem idx esparsos, então o card novo vai no fim.
		idx = max((l.idx or 0 for l in ws.links), default=0)
		novos = [{"type": "Card Break", "label": CARD_LABEL, "hidden": 0, "link_count": len(faltantes)}]
		novos += [{"type": "Link", "label": r, "link_type": "DocType", "link_to": d} for d, r in faltantes]
		for i, linha in enumerate(novos, start=1):
			ws.append("links", {**linha, "idx": idx + i})
		alterado = True
	try:
		blocos = json.loads(ws.content or "[]")
	except Exception:
		blocos = []
	if not any((b.get("data") or {}).get("card_name") == CARD_LABEL for b in blocos):
		blocos.append(
			{
				"id": frappe.generate_hash(length=10),
				"type": "card",
				"data": {"card_name": CARD_LABEL, "col": 4},
			}
		)
		ws.content = json.dumps(blocos, ensure_ascii=False)
		alterado = True
	if alterado:
		ws.flags.ignore_permissions = True
		ws.flags.ignore_links = True
		ws.save()
		frappe.clear_cache()


def _property_setter_se_ausente(doctype, fieldname, propriedade, valor, tipo):
	"""Cria o Property Setter só se não existir (make_property_setter substituiria o que está no site)."""
	if frappe.db.exists("Property Setter", f"{doctype}-{fieldname}-{propriedade}"):
		return
	make_property_setter(doctype, fieldname, propriedade, valor, tipo)


def garantir_campos_na_instalacao():
	"""Cria o que o código da importação Bionexo usa e que, nos sites antigos, vem de patches ou da interface.

	O Frappe marca todos os patches como executados ao instalar um app, então
	`patches/bionexo_to_request_for_quotation.py` nunca roda num site novo e a RFQ ficaria sem `custom_id_bionexo`
	(a consulta da importação falharia com coluna inexistente). Roda no `after_install` e no `after_migrate`, com
	`update=False` e Property Setters só quando ausentes: nunca altera nem sobrescreve o que já existe no site, então
	não tem efeito em produção. As definições dos campos seguem o export de produção.
	"""
	create_custom_fields(
		{
			"Request for Quotation": [
				{
					"fieldname": "custom_tipo_de_contratacao",
					"label": "Tipo de Contratacao",
					"fieldtype": "Select",
					"options": "Edital\nDispensa\nEmergencial\nTécnico Especializado",
					"insert_after": "amended_from",
					"depends_on": 'eval:  doc.naming_series == "SERV-PDC-.YYYY.-";',
					"mandatory_depends_on": 'eval:  doc.naming_series == "SERV-PDC-.YYYY.-";',
				},
				{
					"fieldname": "custom_id_bionexo",
					"label": "ID Bionexo",
					"fieldtype": "Data",
					"insert_after": "custom_tipo_de_contratacao",
				},
				{
					"fieldname": "custom_link_bionexo",
					"label": "Link Bionexo",
					"fieldtype": "Data",
					"options": "URL",
					"insert_after": "custom_id_bionexo",
				},
			],
			"Item": [
				{
					"fieldname": "custom_código_bionexo",
					"label": "Código Bionexo",
					"fieldtype": "Data",
					"insert_after": "stock_uom",
					"hidden": 1,
					"in_standard_filter": 1,
					"in_global_search": 1,
					"in_preview": 1,
					"allow_in_quick_entry": 1,
					"translatable": 1,
				}
			],
		},
		update=False,
	)
	_property_setter_se_ausente("Item", "custom_código_bionexo", "in_list_view", 0, "Check")
	# Mesmo efeito dos patches `bionexo_to_request_for_quotation` e `rfq_suppliers_allow_on_submit`.
	_property_setter_se_ausente("Request for Quotation", "suppliers", "reqd", 0, "Check")
	_property_setter_se_ausente("Request for Quotation", "suppliers", "allow_on_submit", 1, "Check")
	for fieldname in ("supplier_name", "email_id"):
		_property_setter_se_ausente(
			"Request for Quotation Supplier", fieldname, "allow_on_submit", 1, "Check"
		)
	frappe.clear_cache()
