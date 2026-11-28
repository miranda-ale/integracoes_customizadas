# Copyright (c) 2026, StillPulse Tecnologia LTDA and contributors
# See license.txt

"""Phase 2: English `Integ` name for the Role created by the app.

[pre_model_sync]: the DocType and Report JSON files already list the new name in their permissions, so the sync lands on the
renamed Role instead of creating a second one. ``frappe.rename_doc`` rewrites every Link to the Role (Has Role of users,
Reports and Workspaces, Custom DocPerm, standard DocPerm rows) and the ``role_name`` field. It does not rewrite free text
(Server Scripts, saved Reports, Custom Scripts). Idempotent: a step runs only when the old name exists exactly (the database
comparison ignores accents and case). When both names already exist the old Role is merged into the new one.
"""

import frappe

RENAMES = (("Usuário Jurídico", "Integ Legal User"),)


def _exact(name):
	"""Exact, accent-sensitive existence check of a Role."""
	return name in frappe.get_all("Role", filters={"name": name}, pluck="name")


def execute():
	for old, new in RENAMES:
		if not _exact(old):
			continue
		frappe.rename_doc(
			"Role", old, new, force=True, merge=bool(frappe.db.exists("Role", new)), show_alert=False
		)
	frappe.clear_cache()
