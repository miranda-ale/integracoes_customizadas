# Copyright (c) 2026, StillPulse Tecnologia LTDA and contributors
# See license.txt
"""Tests for patch s01 using an in-memory SQLite database; no bench or site is needed.

Only the SQL logic of the merge and the control flow of `execute` are covered. `frappe.rename_doc`
is replaced by a fake that renames only the DocType record (like Frappe, it does not rekey
`tabSingles` and `__Auth` for a Single).
"""

import sqlite3
import sys
import types
import unittest
from unittest.mock import patch

try:
	import frappe
except ImportError:  # pure unit test outside a bench
	frappe = types.ModuleType("frappe")
	sys.modules["frappe"] = frappe

from integracoes_customizadas.patches import s01_rename_datajud_settings as s01

OLD, NEW = s01.OLD_NAME, s01.NEW_NAME


class FakeDB:
	def __init__(self):
		self.conn = sqlite3.connect(":memory:")
		self.conn.execute("create table `tabSingles` (doctype text, field text, value text)")
		self.conn.execute(
			"create table `__Auth` (doctype text, name text, fieldname text, password text, encrypted int,"
			" primary key (doctype, name, fieldname))"
		)
		self.doctypes = set()

	def sql(self, query, values=()):
		return self.conn.execute(query.replace("%s", "?"), values).fetchall()

	def exists(self, doctype, name):
		return name in self.doctypes if doctype == "DocType" else False

	def singles(self, doctype):
		rows = self.sql("select field, value from `tabSingles` where doctype = %s", (doctype,))
		return dict(rows)

	def auth(self, doctype):
		rows = self.sql(
			"select fieldname, password, encrypted from `__Auth` where doctype = %s and name = %s",
			(doctype, doctype),
		)
		return {r[0]: (r[1], r[2]) for r in rows}


class TestRenameDataJudSettings(unittest.TestCase):
	def setUp(self):
		self.db = FakeDB()

		def rename_doc(doctype, old, new, force=False):
			self.db.doctypes.discard(old)
			self.db.doctypes.add(new)

		def delete_doc(doctype, name, **kwargs):
			self.db.doctypes.discard(name)

		patches = [
			patch.object(s01.frappe, "db", self.db, create=True),
			patch.object(s01.frappe, "rename_doc", rename_doc, create=True),
			patch.object(s01.frappe, "delete_doc", delete_doc, create=True),
			patch.object(s01.frappe, "clear_cache", lambda: None, create=True),
		]
		for p in patches:
			p.start()
			self.addCleanup(p.stop)

	def _seed_old(self):
		self.db.doctypes.add(OLD)
		self.db.sql(
			"insert into `tabSingles` values (%s, 'falhas_consecutivas', '3'), (%s, 'circuito_aberto', '1')",
			(OLD, OLD),
		)
		self.db.sql("insert into `__Auth` values (%s, %s, 'api_key', 'ENC-OLD', 1)", (OLD, OLD))

	def test_clean_rename_moves_values_and_password(self):
		self._seed_old()
		s01.execute()
		self.assertEqual(self.db.doctypes, {NEW})
		self.assertEqual(self.db.singles(NEW), {"falhas_consecutivas": "3", "circuito_aberto": "1"})
		self.assertEqual(self.db.auth(NEW), {"api_key": ("ENC-OLD", 1)})
		self.assertEqual(self.db.singles(OLD), {})
		self.assertEqual(self.db.auth(OLD), {})

	def test_new_exists_empty_keeps_old_values(self):
		self._seed_old()
		self.db.doctypes.add(NEW)
		s01.execute()
		self.assertEqual(self.db.doctypes, {NEW})
		self.assertEqual(self.db.singles(NEW), {"falhas_consecutivas": "3", "circuito_aberto": "1"})
		self.assertEqual(self.db.auth(NEW), {"api_key": ("ENC-OLD", 1)})

	def test_partial_new_is_merged_without_overwriting(self):
		self._seed_old()
		self.db.doctypes.add(NEW)
		self.db.sql("insert into `tabSingles` values (%s, 'falhas_consecutivas', '0')", (NEW,))
		s01.execute()
		self.assertEqual(
			self.db.singles(NEW),
			{"falhas_consecutivas": "0", "circuito_aberto": "1"},  # existing new value wins
		)
		self.assertEqual(self.db.auth(NEW), {"api_key": ("ENC-OLD", 1)})
		self.assertEqual(self.db.singles(OLD), {})
		self.assertEqual(self.db.doctypes, {NEW})

	def test_existing_new_password_is_not_overwritten(self):
		self._seed_old()
		self.db.doctypes.add(NEW)
		self.db.sql("insert into `__Auth` values (%s, %s, 'api_key', 'ENC-NEW', 1)", (NEW, NEW))
		s01.execute()
		self.assertEqual(self.db.auth(NEW), {"api_key": ("ENC-NEW", 1)})
		self.assertEqual(self.db.auth(OLD), {})

	def test_second_run_changes_nothing(self):
		self._seed_old()
		s01.execute()
		first = (self.db.singles(NEW), self.db.auth(NEW), set(self.db.doctypes))
		s01.execute()
		self.assertEqual((self.db.singles(NEW), self.db.auth(NEW), set(self.db.doctypes)), first)


if __name__ == "__main__":
	unittest.main()
