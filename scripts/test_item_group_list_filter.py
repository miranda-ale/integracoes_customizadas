"""Smoke test: permission_query_conditions for Material Request with temp UP on existing user."""
import os

import frappe

os.chdir("/home/frappe/frappe-bench/sites")
frappe.init(site="osscesariolange.erpnext.com")
frappe.connect()
frappe.set_user("Administrator")

from integracoes_customizadas.permissions import item_group_access as iga
from frappe.model.db_query import DatabaseQuery

# Use Guest-like approach: create UP on a Purchase User if exists
users = frappe.get_all(
	"Has Role",
	filters={"role": "Purchase User", "parenttype": "User"},
	fields=["parent"],
	limit=20,
)
test_user = None
for u in users:
	if u.parent not in ("Administrator", "Guest") and "@" in u.parent:
		test_user = u.parent
		break

if not test_user:
	# any enabled system user
	for u in frappe.get_all("User", filters={"enabled": 1, "user_type": "System User"}, pluck="name"):
		if u != "Administrator":
			test_user = u
			break

print("test_user:", test_user)
assert test_user

groups = frappe.get_all("Item Group", pluck="name")
# pick group that actually appears on MR items
row = frappe.db.sql(
	"""
	SELECT COALESCE(NULLIF(mri.item_group,''), i.item_group) AS ig, COUNT(*) c
	FROM `tabMaterial Request Item` mri
	LEFT JOIN `tabItem` i ON i.name = mri.item_code
	WHERE COALESCE(NULLIF(mri.item_group,''), i.item_group) IS NOT NULL
	GROUP BY 1
	ORDER BY c DESC
	LIMIT 5
	""",
	as_dict=True,
)
print("MR item groups top:", row)
target_group = row[0].ig if row else (groups[0] if groups else None)
print("target_group:", target_group)

# Snapshot existing Item Group UPs for this user to restore later
existing = frappe.get_all(
	"User Permission",
	filters={"user": test_user, "allow": "Item Group"},
	fields=["name", "for_value", "apply_to_all_doctypes", "applicable_for", "hide_descendants"],
)
print("existing IG UPs:", existing)

# Remove existing IG UPs temporarily
for e in existing:
	frappe.delete_doc("User Permission", e.name, ignore_permissions=True, force=True)

up = frappe.get_doc(
	{
		"doctype": "User Permission",
		"user": test_user,
		"allow": "Item Group",
		"for_value": target_group,
		"apply_to_all_doctypes": 1,
		"hide_descendants": 0,
	}
)
up.insert(ignore_permissions=True)
frappe.db.commit()
frappe.cache.hdel("user_permissions", test_user)
frappe.clear_cache(user=test_user)

# Admin total
frappe.set_user("Administrator")
total = frappe.db.count("Material Request")
print("admin total MR:", total)

# Test user
frappe.set_user(test_user)
allowed = iga.get_allowed_item_groups(test_user, "Material Request")
print("allowed count:", len(allowed or []), "sample:", (allowed or [])[:5])
cond = iga.permission_query_conditions(user=test_user, doctype="Material Request")
print("has condition:", bool(cond), "len:", len(cond or ""))

q = DatabaseQuery("Material Request")
q.user = test_user
result = q.execute(fields=["name"], limit_page_length=100, as_list=False)
print("filtered MR count (page 100):", len(result or []))

# Validate each returned MR only has allowed groups
bad = 0
for d in result or []:
	items = frappe.get_all(
		"Material Request Item",
		filters={"parent": d.name},
		fields=["item_code", "item_group"],
	)
	for it in items:
		ig = it.item_group or frappe.db.get_value("Item", it.item_code, "item_group")
		if ig and allowed and ig not in allowed:
			bad += 1
			print("LEAK", d.name, it.item_code, ig)
			break
print("leaks in filtered list:", bad)

# Restore: delete test UP, re-create previous
frappe.set_user("Administrator")
frappe.delete_doc("User Permission", up.name, ignore_permissions=True, force=True)
for e in existing:
	frappe.get_doc(
		{
			"doctype": "User Permission",
			"user": test_user,
			"allow": "Item Group",
			"for_value": e.for_value,
			"apply_to_all_doctypes": e.apply_to_all_doctypes,
			"applicable_for": e.applicable_for,
			"hide_descendants": e.hide_descendants,
		}
	).insert(ignore_permissions=True)
frappe.db.commit()
frappe.cache.hdel("user_permissions", test_user)
print("restored UPs, DONE")
frappe.destroy()
