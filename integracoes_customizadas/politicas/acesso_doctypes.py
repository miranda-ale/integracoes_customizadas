# Copyright (c) 2026, StillPulse and contributors
# For license information, please see license.txt
"""Política de acesso: todo DocType dos apps customizados tem um local de acesso, visível só a quem pode lê-lo.

Um DocType (não filho) está "acessível" quando:
1. aparece como link ou atalho de DocType num Workspace público e não oculto;
2. algum papel tem permissão de leitura nele (DocPerm ou Custom DocPerm);
3. o Workspace que o contém não é restrito a papéis que nenhum leitor do DocType possui.

A visibilidade em si é do Frappe: um link só é exibido a quem tem permissão de leitura no DocType, e o
Workspace só aparece a quem tem algum dos papéis listados nele (lista vazia = todos). Por isso a política
não cria permissões; apenas aponta DocTypes órfãos ou inalcançáveis. Roda como aviso a cada `migrate` e é
exigida pelo teste `tests/test_politica_acesso.py`.
"""

import frappe

APPS_UPSTREAM = {"frappe", "erpnext", "hrms"}
# DocTypes de apoio sem lista própria que não precisam de atalho (justificar cada entrada).
EXCECOES = frozenset()


def doctypes_dos_apps_customizados():
	"""DocTypes não filhos e não virtuais dos módulos dos apps customizados instalados."""
	apps = set(frappe.get_installed_apps()) - APPS_UPSTREAM
	modulos = frappe.get_all("Module Def", filters={"app_name": ["in", list(apps)]}, pluck="name")
	if not modulos:
		return []
	return frappe.get_all(
		"DocType",
		filters={"module": ["in", modulos], "istable": 0, "is_virtual": 0},
		fields=["name", "module", "issingle"],
		order_by="module, name",
	)


def _workspaces_publicos():
	"""{workspace: (papéis restritos, {DocTypes linkados})} só dos públicos e visíveis na barra lateral."""
	resultado = {}
	for nome in frappe.get_all("Workspace", filters={"public": 1, "is_hidden": 0}, pluck="name"):
		ws = frappe.get_doc("Workspace", nome)
		alvos = {l.link_to for l in ws.links if l.type == "Link" and l.link_type == "DocType" and l.link_to}
		alvos |= {s.link_to for s in ws.shortcuts if s.type == "DocType" and s.link_to}
		resultado[nome] = ({r.role for r in ws.roles}, alvos)
	return resultado


def _papeis_leitores(doctype):
	papeis = set(
		frappe.get_all("Custom DocPerm", filters={"parent": doctype, "read": 1, "permlevel": 0}, pluck="role")
	)
	papeis |= set(
		frappe.get_all("DocPerm", filters={"parent": doctype, "read": 1, "permlevel": 0}, pluck="role")
	)
	return papeis


def verificar():
	"""Retorna {problema: [descrições]} para os DocTypes que violam a política."""
	workspaces = _workspaces_publicos()
	problemas = {"sem_atalho": [], "sem_leitor": [], "workspace_inalcancavel": []}
	for d in doctypes_dos_apps_customizados():
		if d.name in EXCECOES:
			continue
		onde = {nome: roles for nome, (roles, alvos) in workspaces.items() if d.name in alvos}
		if not onde:
			problemas["sem_atalho"].append(f"{d.module} | {d.name}")
			continue
		leitores = _papeis_leitores(d.name)
		if not leitores:
			problemas["sem_leitor"].append(f"{d.module} | {d.name}")
		elif all(roles and not (roles & leitores) for roles in onde.values()):
			problemas["workspace_inalcancavel"].append(f"{d.name} -> {', '.join(sorted(onde))}")
	return problemas


def avisar_violacoes():
	"""after_migrate: agenda a verificação para o commit final, depois que todos os apps montaram seus cards."""
	frappe.db.after_commit.add(_registrar_violacoes)


def _registrar_violacoes():
	problemas = verificar()
	if not any(problemas.values()):
		return
	linhas = [f"[{tipo}] {item}" for tipo, itens in problemas.items() for item in itens]
	print("Política de acesso a DocTypes violada:\n  " + "\n  ".join(linhas))
