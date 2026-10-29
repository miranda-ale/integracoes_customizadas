"""Ajustes de permissões que precisam persistir após a sincronização dos DocTypes."""

import json
from pathlib import Path

import frappe

from integracoes_customizadas.juridico.datajud import _descricao_movimento

WORKSPACE = "Jurídico"
BLOCOS_DIR = Path(__file__).resolve().parent / "custom_blocks"
INDICADORES_BLOCK = "Juridico Indicadores"
INDICADORES_ID = "juridico-indicadores-block"
PARECERES_ID = "juridico-atalho-pareceres"
PARECERES_LABEL = "Pareceres Jurídicos"
PARECERES_DOCTYPE = "CLM Legal Evaluation"
ROLES_WORKSPACE = (
	"Usuário Jurídico",
	"System Manager",
	"HR Manager",
	"HR User",
	"CLM Administrator",
	"CLM Manager",
	"CLM User",
)


def after_migrate():
	ensure_indicadores_block()
	ensure_juridico_workspace()
	if not frappe.db.exists("DocType", "Processo Judicial"):
		return
	if frappe.db.has_column("Processo Judicial", "status_processo"):
		for name in frappe.get_all(
			"Processo Judicial", filters={"status_processo": ["is", "not set"]}, pluck="name"
		):
			frappe.db.set_value(
				"Processo Judicial", name, "status_processo", "Em andamento", update_modified=False
			)
	if frappe.db.has_column("Processo Judicial", "nome_parte"):
		campos = {
			"Employee": "employee_name",
			"Customer": "customer_name",
			"Supplier": "supplier_name",
			"Terceiros": "full_name",
		}
		for row in frappe.get_all(
			"Processo Judicial",
			filters={"parte": ["is", "set"], "nome_parte": ["is", "not set"]},
			fields=["name", "tipo_parte", "parte"],
		):
			if row.tipo_parte in campos:
				doctype = "Contact" if row.tipo_parte == "Terceiros" else row.tipo_parte
				nome = frappe.db.get_value(doctype, row.parte, campos[row.tipo_parte])
				if nome:
					frappe.db.set_value(
						"Processo Judicial", row.name, "nome_parte", nome, update_modified=False
					)
	if frappe.db.has_column("Processo Judicial", "doctype_parte"):
		for row in frappe.get_all("Processo Judicial", fields=["name", "tipo_parte", "doctype_parte"]):
			doctype = "Contact" if row.tipo_parte == "Terceiros" else row.tipo_parte
			if row.doctype_parte != doctype:
				frappe.db.set_value(
					"Processo Judicial", row.name, "doctype_parte", doctype, update_modified=False
				)
	if frappe.db.has_column("Processo Judicial Movimento", "descricao"):
		for row in frappe.get_all(
			"Processo Judicial Movimento",
			fields=["name", "nome", "descricao", "complementos_tabelados"],
		):
			try:
				complementos = json.loads(row.complementos_tabelados or "[]")
			except (TypeError, ValueError):
				complementos = []
			descricao = _descricao_movimento({"nome": row.nome, "complementosTabelados": complementos})
			if row.descricao != descricao:
				frappe.db.set_value(
					"Processo Judicial Movimento", row.name, "descricao", descricao, update_modified=False
				)
	frappe.clear_cache(doctype="Processo Judicial")


def ensure_indicadores_block():
	"""Cria/atualiza o Custom HTML Block dos indicadores (HTML/JS/CSS versionados no app)."""
	valores = {
		"html": (BLOCOS_DIR / "indicadores_juridico.html").read_text(encoding="utf-8"),
		"script": (BLOCOS_DIR / "indicadores_juridico.js").read_text(encoding="utf-8"),
		"style": (BLOCOS_DIR / "style.css").read_text(encoding="utf-8"),
		"private": 0,
	}
	if frappe.db.exists("Custom HTML Block", INDICADORES_BLOCK):
		doc = frappe.get_doc("Custom HTML Block", INDICADORES_BLOCK)
		if all((doc.get(k) or "") == v for k, v in valores.items()):
			return
		doc.update(valores)
	else:
		doc = frappe.get_doc({"doctype": "Custom HTML Block", "__newname": INDICADORES_BLOCK, **valores})
		doc.flags.name = INDICADORES_BLOCK
	doc.save(ignore_permissions=True)


def ensure_juridico_workspace():
	"""Painel de indicadores no topo, atalho de Pareceres Juridicos (CLM) e restricao por papeis.

	Idempotente: so salva (e limpa cache) quando algo difere do desejado. Os cartoes numericos
	antigos saem do layout, pois o painel os substitui; os documentos Number Card continuam existindo.
	"""
	if not frappe.db.exists("Workspace", WORKSPACE):
		return
	ws = frappe.get_doc("Workspace", WORKSPACE)
	alterado = False

	try:
		blocos = json.loads(ws.content or "[]")
	except ValueError:
		blocos = []
	blocos = [
		b
		for b in blocos
		if b.get("type") != "number_card" and b.get("id") not in (INDICADORES_ID, PARECERES_ID)
	]
	blocos.insert(
		0,
		{
			"id": INDICADORES_ID,
			"type": "custom_block",
			"data": {"custom_block_name": INDICADORES_BLOCK, "col": 12},
		},
	)

	if frappe.db.exists("DocType", PARECERES_DOCTYPE):
		if not any(r.label == PARECERES_LABEL for r in ws.shortcuts):
			ws.append(
				"shortcuts",
				{
					"label": PARECERES_LABEL,
					"type": "DocType",
					"link_to": PARECERES_DOCTYPE,
					"doc_view": "List",
					"color": "Orange",
				},
			)
			alterado = True
		ultimo_atalho = max(
			(i for i, b in enumerate(blocos) if b.get("type") == "shortcut"), default=len(blocos) - 1
		)
		blocos.insert(
			ultimo_atalho + 1,
			{"id": PARECERES_ID, "type": "shortcut", "data": {"shortcut_name": PARECERES_LABEL, "col": 3}},
		)

	novo_content = json.dumps(blocos, ensure_ascii=False)
	if novo_content != ws.content:
		ws.content = novo_content
		alterado = True

	if not any(r.custom_block_name == INDICADORES_BLOCK for r in ws.custom_blocks):
		ws.append("custom_blocks", {"custom_block_name": INDICADORES_BLOCK, "label": INDICADORES_BLOCK})
		alterado = True

	if ws.number_cards:
		ws.set("number_cards", [])
		alterado = True

	desejados = [r for r in ROLES_WORKSPACE if frappe.db.exists("Role", r)]
	if sorted(r.role for r in ws.roles) != sorted(desejados):
		ws.set("roles", [{"role": r} for r in desejados])
		alterado = True

	if alterado:
		ws.flags.ignore_permissions = True
		ws.flags.ignore_links = True
		ws.save()
		frappe.clear_cache()
