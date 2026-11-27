# Copyright (c) 2026, StillPulse Tecnologia LTDA and contributors
# See license.txt

import frappe

# (doctype, old name, new name): names become plain ASCII, accents stay only in labels.
RENAMES = (
	("Report", "Relação de Processos", "Relacao de Processos"),
	("Report", "Provisão de Processos", "Provisao de Processos"),
	("Workspace", "Jurídico", "Juridico"),
)


def execute():
	"""Rename the accented Juridico Reports and Workspace to ASCII names.

	Runs before model sync so existing sites keep user-level data (prepared reports, saved filters,
	workspace customizations): `rename_doc` rewrites every link to the old names. Files on disk are
	already renamed in the repository. Idempotent: skips names that are gone or already migrated.
	"""
	for doctype, old, new in RENAMES:
		if not frappe.db.exists(doctype, old):
			continue
		if frappe.db.exists(doctype, new):
			# Both exist (e.g. the sync ran first): drop the legacy record, the new one is canonical.
			frappe.delete_doc(doctype, old, force=True, ignore_permissions=True)
		else:
			frappe.rename_doc(doctype, old, new, force=True)

	frappe.clear_cache()
