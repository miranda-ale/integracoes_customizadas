# Copyright (c) 2026, StillPulse Tecnologia LTDA and contributors
# For license information, please see license.txt

"""Custom Field ownership: a Custom Field has exactly one app that ships it.

The 35 Employee/Designation fields that both apps used to ship belong to rh_brasil (its hooks list them by name). This
app keeps only its own, and its export filter must list exactly the fixture entries, otherwise `bench export-fixtures`
would write the shared ones back.
"""

import json
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

HOOKS_FIXTURE = "Custom Field"


def _names(path):
	return {row["name"] for row in json.loads(Path(path).read_text(encoding="utf-8"))}


class TestFixtureOwnership(FrappeTestCase):
	def test_export_filter_lists_exactly_the_shipped_fields(self):
		from integracoes_customizadas import hooks

		listed = set()
		for entry in hooks.fixtures:
			if entry["dt"] != HOOKS_FIXTURE:
				continue
			for field, operator, value in entry["filters"]:
				self.assertEqual(
					(field, operator), ("name", "in"), "filter Custom Fields by name, not by DocType"
				)
				listed |= set(value)
		shipped = _names(frappe.get_app_path("integracoes_customizadas", "fixtures", "custom_field.json"))
		self.assertEqual(listed, shipped)

	def test_no_field_is_shipped_by_both_apps(self):
		if "rh_brasil" not in frappe.get_installed_apps():
			self.skipTest("rh_brasil is not installed")
		ours = _names(frappe.get_app_path("integracoes_customizadas", "fixtures", "custom_field.json"))
		theirs = _names(frappe.get_app_path("rh_brasil", "fixtures", "custom_field.json"))
		self.assertEqual(
			sorted(ours & theirs), [], "these Custom Fields belong to rh_brasil: remove them here"
		)
