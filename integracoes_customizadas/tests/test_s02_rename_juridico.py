# Copyright (c) 2026, StillPulse Tecnologia LTDA and contributors
# See license.txt

"""Phase 2: patch s02 renames accented Juridico records (Reports and the Workspace) to ASCII names instead of deleting them.

`frappe.db.exists` ignores accents (utf8mb4_unicode_ci), so the old check treated the ASCII name as present
while only the accented record existed, and the patch deleted the legacy record.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from integracoes_customizadas.patches import s02_rename_juridico_reports_and_workspace as s02

OLD = "Integ Test Relação S02"
NEW = "Integ Test Relacao S02"
OLD_WS = "Integ Test Jurídico S02"
NEW_WS = "Integ Test Juridico S02"


def _names(doctype, **filters):
	return frappe.get_all(doctype, filters=filters, pluck="name")


def _exact_names(doctype):
	"""All names of a doctype, compared exactly in Python (the database collation ignores accents)."""
	return frappe.get_all(doctype, pluck="name")


class TestS02RenameJuridico(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self._cleanup()
		self.addCleanup(self._cleanup)

		report = frappe.get_doc(
			{
				"doctype": "Report",
				"report_name": OLD,
				"ref_doctype": "ToDo",
				"report_type": "Query Report",
				"is_standard": "No",
				"module": "Integracoes Customizadas",
				"query": "select 1 as one",
			}
		).insert(ignore_permissions=True)
		self.assertEqual(report.name, OLD)
		frappe.get_doc(
			{"doctype": "Custom Role", "report": OLD, "roles": [{"role": "System Manager"}]}
		).insert(ignore_permissions=True)

		self.patch_renames = patch.object(s02, "RENAMES", (("Report", OLD, NEW),))
		self.patch_renames.start()
		self.addCleanup(self.patch_renames.stop)

	def _cleanup(self):
		for name in (OLD, NEW):
			for custom_role in frappe.get_all("Custom Role", filters={"report": name}, pluck="name"):
				frappe.delete_doc("Custom Role", custom_role, force=True, ignore_permissions=True)
			if name in _exact_names("Report"):
				frappe.delete_doc("Report", name, force=True, ignore_permissions=True)
			frappe.db.delete("Deleted Document", {"deleted_doctype": "Report", "deleted_name": name})

	def test_accented_report_is_renamed_not_deleted(self):
		s02.execute()

		self.assertIn(NEW, _exact_names("Report"))
		self.assertNotIn(OLD, _exact_names("Report"))

	def test_custom_role_follows_the_rename(self):
		s02.execute()

		custom_roles = frappe.get_all("Custom Role", filters={"report": NEW}, pluck="report")
		self.assertEqual(custom_roles, [NEW])

	def test_no_deleted_document_row_for_the_legacy_report(self):
		s02.execute()

		deleted = frappe.get_all(
			"Deleted Document", filters={"deleted_doctype": "Report"}, pluck="deleted_name"
		)
		self.assertNotIn(OLD, deleted)

	def test_second_run_changes_nothing(self):
		s02.execute()
		s02.execute()

		self.assertEqual(frappe.get_all("Report", filters={"name": NEW}, pluck="name"), [NEW])
		deleted = frappe.get_all(
			"Deleted Document",
			filters={"deleted_doctype": "Report", "deleted_name": OLD},
			pluck="name",
		)
		self.assertEqual(deleted, [])


class TestS02RenameJuridicoWorkspace(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self._cleanup()
		self.addCleanup(self._cleanup)

		workspace = frappe.get_doc(
			{
				"doctype": "Workspace",
				"label": OLD_WS,
				"title": OLD_WS,
				"public": 1,
				"module": "Integracoes Customizadas",
				"content": "[]",
			}
		).insert(ignore_permissions=True)
		self.assertEqual(workspace.name, OLD_WS)
		self.creation_before = frappe.db.get_value("Workspace", OLD_WS, "creation")

		self.patch_renames = patch.object(s02, "RENAMES", (("Workspace", OLD_WS, NEW_WS),))
		self.patch_renames.start()
		self.addCleanup(self.patch_renames.stop)

	def _cleanup(self):
		for name in (OLD_WS, NEW_WS):
			if name in _exact_names("Workspace"):
				frappe.delete_doc("Workspace", name, force=True, ignore_permissions=True)
			frappe.db.delete("Deleted Document", {"deleted_doctype": "Workspace", "deleted_name": name})

	def test_accented_workspace_is_renamed_not_deleted(self):
		s02.execute()

		self.assertIn(NEW_WS, _exact_names("Workspace"))
		self.assertNotIn(OLD_WS, _exact_names("Workspace"))

	def test_rename_keeps_the_creation_timestamp(self):
		s02.execute()

		self.assertEqual(frappe.db.get_value("Workspace", NEW_WS, "creation"), self.creation_before)

	def test_no_deleted_document_row_for_the_legacy_workspace(self):
		s02.execute()

		deleted = frappe.get_all(
			"Deleted Document", filters={"deleted_doctype": "Workspace"}, pluck="deleted_name"
		)
		self.assertNotIn(OLD_WS, deleted)
