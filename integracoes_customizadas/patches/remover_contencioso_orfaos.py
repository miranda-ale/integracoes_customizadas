"""Remove do banco os resquicios seguros do antigo modulo Contencioso (sem codigo no repositorio).

Remove Reports do modulo, DocTypes CJ * e papeis CJ sem usuario. As tabelas CJ * so guardavam
linhas orfas do ProcJud-2026-00001 (Processo Judicial que ja nao existe); elas sao apagadas antes.
Tabelas com linhas de pais existentes e papeis em uso sao preservados e apenas registrados.
"""

import frappe

MODULO = "Contencioso"
PROCESSO_ORFAO = "ProcJud-2026-00001"
PAPEIS = ("CJ Analista Jurídico", "CJ Gestor Jurídico", "CJ Administrador", "CJ Visualizador")


def execute():
	_remover_reports()
	_remover_doctypes_vazios()
	_remover_papeis_sem_usuario()
	_remover_modulo_vazio()
	frappe.clear_cache()


def _remover(doctype, name):
	try:
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
		return True
	except Exception:
		frappe.log_error(title=f"remover_contencioso_orfaos: {doctype} {name}")
		return False


def _remover_reports():
	for name in frappe.get_all("Report", filters={"module": MODULO}, pluck="name"):
		_remover("Report", name)


def _remover_doctypes_vazios():
	existe = frappe.db.exists("Processo Judicial", PROCESSO_ORFAO)
	for name in frappe.get_all("DocType", filters={"module": MODULO, "name": ["like", "CJ %"]}, pluck="name"):
		if not existe and frappe.db.table_exists(name):
			frappe.db.delete(name, {"parent": PROCESSO_ORFAO})
		if frappe.db.table_exists(name) and frappe.db.count(name):
			print(f"Contencioso: {name} mantido (possui dados)")
			continue
		_remover("DocType", name)


def _remover_papeis_sem_usuario():
	for papel in PAPEIS:
		if not frappe.db.exists("Role", papel):
			continue
		if frappe.db.exists("Has Role", {"role": papel, "parenttype": "User"}):
			print(f"Contencioso: papel {papel} mantido (possui usuarios)")
			continue
		frappe.db.delete("Custom DocPerm", {"role": papel})
		frappe.db.delete("DocPerm", {"role": papel})
		frappe.db.delete("Has Role", {"role": papel})
		_remover("Role", papel)


def _remover_modulo_vazio():
	if not frappe.db.exists("Module Def", MODULO):
		return
	if frappe.db.exists("DocType", {"module": MODULO}) or frappe.db.exists("Report", {"module": MODULO}):
		return
	_remover("Module Def", MODULO)
