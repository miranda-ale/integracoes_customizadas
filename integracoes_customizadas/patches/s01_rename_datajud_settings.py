# Copyright (c) 2026, StillPulse Tecnologia LTDA and contributors
# See license.txt

import frappe

OLD_NAME = "Configurações DataJud"
NEW_NAME = "DataJud Settings"


def execute():
	"""Rename the DataJud Single DocType to an ASCII name.

	Runs before model sync so the existing configuration (including the encrypted API key and the
	circuit breaker state) survives. The directory and files are already renamed in the repository,
	so only database records are touched. Safe to retry: stored values are merged, never overwritten,
	and running it again changes nothing.
	"""
	old_exists = frappe.db.exists("DocType", OLD_NAME)
	new_exists = frappe.db.exists("DocType", NEW_NAME)

	if old_exists and not new_exists:
		frappe.rename_doc("DocType", OLD_NAME, NEW_NAME, force=True)
		_move_single_values()
	elif new_exists:
		# Partial earlier run or model sync already created the new DocType: merge first, then drop
		# the legacy DocType, so no stored value is lost.
		_move_single_values()
		if old_exists:
			frappe.delete_doc("DocType", OLD_NAME, force=True, ignore_permissions=True)

	frappe.clear_cache()


def _move_single_values():
	"""Merge the Single values and the encrypted password rows of the old name into the new name.

	`rename_doc` does not rekey `tabSingles` and `__Auth` for a Single DocType, where the DocType name
	is also the document name. Only the (field) / (fieldname) keys missing under the new name are copied
	(an existing value under the new name always wins, and the encrypted password is copied as stored),
	then the remaining rows of the old name are removed. Idempotent.
	"""
	frappe.db.sql(
		"""
		insert into `tabSingles` (`doctype`, `field`, `value`)
		select %s, o.`field`, o.`value` from `tabSingles` o
		where o.`doctype` = %s
		and not exists (
			select 1 from `tabSingles` n where n.`doctype` = %s and n.`field` = o.`field`
		)
		""",
		(NEW_NAME, OLD_NAME, NEW_NAME),
	)
	frappe.db.sql("delete from `tabSingles` where `doctype` = %s", (OLD_NAME,))

	frappe.db.sql(
		"""
		insert into `__Auth` (`doctype`, `name`, `fieldname`, `password`, `encrypted`)
		select %s, %s, o.`fieldname`, o.`password`, o.`encrypted` from `__Auth` o
		where o.`doctype` = %s and o.`name` = %s
		and not exists (
			select 1 from `__Auth` n
			where n.`doctype` = %s and n.`name` = %s and n.`fieldname` = o.`fieldname`
		)
		""",
		(NEW_NAME, NEW_NAME, OLD_NAME, OLD_NAME, NEW_NAME, NEW_NAME),
	)
	frappe.db.sql("delete from `__Auth` where `doctype` = %s and `name` = %s", (OLD_NAME, OLD_NAME))
