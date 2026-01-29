# Copyright (c) 2026
# Garante que DocTypes do Contencioso existam no banco (evita DoesNotExistError após fixture não importá-los).

import frappe
from frappe.modules.import_file import import_file_by_path


CONTENCIOSO_DOCTYPES = [
	"CJ Snapshot de Risco",
	"Processo Judicial",
	"CJ Parte",
	"CJ Evento",
	"CJ Prazo",
	"CJ Audiencia",
	"CJ Documento",
	"CJ Item Financeiro",
	"CJ Integracao",
]


def ensure_contencioso_doctypes():
	"""Se algum DocType do Contencioso não existir no banco, importa do filesystem (após migrate)."""
	for doctype_name in CONTENCIOSO_DOCTYPES:
		if frappe.db.exists("DocType", doctype_name):
			continue
		# Nome do módulo: ex. "CJ Snapshot de Risco" -> cj_snapshot_de_risco
		module_name = doctype_name.replace(" ", "_").lower()
		# Path: integracoes_customizadas/contencioso/doctype/<module>/<module>.json
		path = frappe.get_app_path(
			"integracoes_customizadas",
			"contencioso",
			"doctype",
			module_name,
			f"{module_name}.json",
		)
		try:
			import_file_by_path(
				path,
				force=True,
				ignore_version=True,
				data_import=False,
			)
			frappe.db.commit()
			frappe.logger("contencioso").info("DocType %s criado a partir do filesystem", doctype_name)
		except Exception as e:
			frappe.log_error(
				title=f"Erro ao sincronizar DocType {doctype_name}",
				message=str(e),
			)
