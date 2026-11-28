# Copyright (c) 2026, StillPulse Tecnologia LTDA and contributors
# See license.txt

import frappe

# (doctype, old name, new name): names become plain ASCII, accents stay only in labels.
RENAMES = (
	("Report", "Relação de Processos", "Relacao de Processos"),
	("Report", "Provisão de Processos", "Provisao de Processos"),
	("Workspace", "Jurídico", "Juridico"),
)


def _exact(doctype, name):
	"""Exact, accent-sensitive existence check.

	`frappe.db.exists` ignores accents (utf8mb4_unicode_ci): with only the accented record present it also answers True for
	the ASCII name, which made the patch delete the legacy Report instead of renaming it. The Python comparison on the
	returned names makes the check exact without building SQL by hand.
	"""
	return name in frappe.get_all(doctype, filters={"name": name}, pluck="name")


def execute():
	"""Rename the accented Juridico Reports and Workspace to ASCII names.

	Runs before model sync so existing sites keep user-level data (prepared reports, saved filters,
	workspace customizations, Custom Roles): `rename_doc` rewrites every link to the old names. Files on disk are
	already renamed in the repository. Idempotent: skips names that are gone or already migrated.
	"""
	for doctype, old, new in RENAMES:
		if not _exact(doctype, old):
			continue
		if _exact(doctype, new):
			# Both exist exactly (e.g. the sync ran first): drop the legacy record, the new one is canonical.
			frappe.delete_doc(doctype, old, force=True, ignore_permissions=True)
		else:
			# Accent-only differences are not a clash for `rename_doc` (its own check compares exactly), so it renames.
			frappe.rename_doc(doctype, old, new, force=True, ignore_if_exists=True, show_alert=False)

	frappe.clear_cache()
