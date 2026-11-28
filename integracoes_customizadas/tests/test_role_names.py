# Copyright (c) 2026, StillPulse Tecnologia LTDA and contributors
# See license.txt

"""Phase 2: the Role created by the app carries the name the s04 patch renames to."""

import frappe
from frappe.tests.utils import FrappeTestCase

from integracoes_customizadas.juridico.setup import ROLES_WORKSPACE
from integracoes_customizadas.patches.s04_rename_roles import RENAMES, execute


class TestRoleNames(FrappeTestCase):
	def test_code_uses_the_new_name(self):
		self.assertIn(RENAMES[0][1], str(ROLES_WORKSPACE))

	def test_patch_renames_links_and_is_idempotent(self):
		old, new = RENAMES[0]
		frappe.db.delete("Role", {"name": ("in", [old, new])})
		frappe.get_doc({"doctype": "Role", "role_name": old, "desk_access": 1}).insert()
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "role-rename-integ@example.com",
				"first_name": "Role Rename",
				"roles": [{"role": old}],
				"send_welcome_email": 0,
			}
		).insert()
		execute()
		self.assertNotIn(old, frappe.get_all("Role", pluck="name"))
		self.assertEqual(frappe.db.get_value("Role", new, "role_name"), new)
		self.assertIn(new, frappe.get_roles(user.name))
		execute()
		self.assertEqual(
			frappe.get_all("Has Role", filters={"parent": user.name, "role": new}, pluck="role"), [new]
		)

	def test_patch_merges_when_both_names_exist(self):
		old, new = RENAMES[0]
		frappe.db.delete("Role", {"name": ("in", [old, new])})
		for name in (old, new):
			frappe.get_doc({"doctype": "Role", "role_name": name, "desk_access": 1}).insert()
		execute()
		self.assertEqual(frappe.get_all("Role", filters={"name": ("in", [old, new])}, pluck="name"), [new])
