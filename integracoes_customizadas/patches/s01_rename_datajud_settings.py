# Copyright (c) 2026, StillPulse Tecnologia LTDA and contributors
# See license.txt

import frappe

OLD_NAME = "Configurações DataJud"
NEW_NAME = "DataJud Settings"


def execute():
	"""Rename the DataJud Single DocType to an ASCII name.

	Runs before model sync so the existing configuration (including the encrypted API key and the
	circuit breaker state) survives. The directory and files are already renamed in the repository,
	so only database records are touched. Safe to retry: it does nothing once the old name is gone.
	"""
	if not frappe.db.exists("DocType", OLD_NAME):
		return

	if frappe.db.exists("DocType", NEW_NAME):
		# The new DocType already exists (for example created by a partial run): keep the new one
		# and only carry over the Single values that were not moved yet.
		_move_single_values()
		frappe.delete_doc("DocType", OLD_NAME, force=True, ignore_permissions=True)
	else:
		frappe.rename_doc("DocType", OLD_NAME, NEW_NAME, force=True)
		_move_single_values()

	frappe.clear_cache()


def _move_single_values():
	"""Move Single values and the encrypted password rows to the new DocType name.

	`rename_doc` does not rekey `tabSingles` and `__Auth` for a Single DocType, where the DocType
	name is also the document name, so the stored values would be orphaned without this.
	"""
	if not frappe.db.sql("select 1 from `tabSingles` where doctype=%s limit 1", (NEW_NAME,)):
		frappe.db.sql("update `tabSingles` set doctype=%s where doctype=%s", (NEW_NAME, OLD_NAME))
	if not frappe.db.sql("select 1 from `__Auth` where doctype=%s limit 1", (NEW_NAME,)):
		frappe.db.sql(
			"update `__Auth` set doctype=%s, name=%s where doctype=%s and name=%s",
			(NEW_NAME, NEW_NAME, OLD_NAME, OLD_NAME),
		)
