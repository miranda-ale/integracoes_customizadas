"""Card "Bionexo" no workspace Buying com o atalho da Importacao Bionexo (idempotente)."""

import json

import frappe

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
