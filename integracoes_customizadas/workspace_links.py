# Copyright (c) 2026, StillPulse Tecnologia LTDA and contributors
# For license information, please see license.txt

"""Additive Workspace links.

Production Workspaces are partly hand-made; a new site has none of them, so the DocTypes of the app have no access point
(see the access policy in ``integracoes_customizadas``). ``ensure_workspace_links`` creates the public Workspace when it
is missing and appends only the links that are absent. It never removes, reorders or renames what is already there, and
it saves (and clears the cache) only when something changed. Idempotent.
"""

import json
import secrets

import frappe


def ensure_workspace_links(name, module, cards, icon=None):
	"""``cards`` is ``[(card label, [DocType names])]``. DocTypes that do not exist on the site are skipped."""
	exists = frappe.db.exists("Workspace", name)
	if exists:
		ws = frappe.get_doc("Workspace", name)
	else:
		ws = frappe.get_doc(
			{
				"doctype": "Workspace",
				"name": name,
				"label": name,
				"title": name,
				"module": module,
				"public": 1,
				"is_hidden": 0,
				"icon": icon or "",
				"content": "[]",
			}
		)
	changed = not exists
	blocks = _blocks(ws.content)
	present = {(link.link_type, link.link_to) for link in ws.links if link.type == "Link" and link.link_to}
	for label, doctypes in cards:
		rows = [
			{"type": "Link", "label": dt, "link_type": "DocType", "link_to": dt, "hidden": 0, "onboard": 0}
			for dt in doctypes
			if frappe.db.exists("DocType", dt) and ("DocType", dt) not in present
		]
		if not rows:
			continue
		links = [link.as_dict(no_default_fields=True) for link in ws.links]
		end = _end_of_card(links, label)
		if end is None:
			links.append({"type": "Card Break", "label": label, "hidden": 0, "onboard": 0})
			links.extend(rows)
			blocks.append(
				{"id": secrets.token_hex(5), "type": "card", "data": {"card_name": label, "col": 4}}
			)
		else:
			links[end:end] = rows
		ws.set("links", links)
		changed = True
	if not changed:
		return
	ws.content = json.dumps(blocks, ensure_ascii=False)
	ws.flags.ignore_permissions = True
	ws.flags.ignore_links = True
	ws.save() if exists else ws.insert()
	frappe.clear_cache()


def _blocks(content):
	try:
		return json.loads(content or "[]")
	except ValueError:
		return []


def _end_of_card(links, label):
	"""Index right after the last link of the card ``label`` (None when the card does not exist)."""
	start = next(
		(i for i, row in enumerate(links) if row.get("type") == "Card Break" and row.get("label") == label),
		None,
	)
	if start is None:
		return None
	for i in range(start + 1, len(links)):
		if links[i].get("type") == "Card Break":
			return i
	return len(links)


# DocTypes of this app that the access policy found without a Workspace on a new site.
WORKSPACES = (
	("Integ Exams", "Provas", (("Provas", ("Prova", "Questao", "Disciplina", "Edital")),)),
	(
		"Integ Integrations",
		"Integracoes Customizadas",
		(
			("WhatsApp", ("Configuracoes WhatsApp", "Modelo WhatsApp", "Envio WhatsApp")),
			("Cadastros", ("Tipo de Deficiencia",)),
		),
	),
	("Integ Legal", "Juridico", (("Judicial", ("DataJud Sync Log",)),)),
)


def ensure_workspaces():
	for name, module, cards in WORKSPACES:
		ensure_workspace_links(name, module, cards)
