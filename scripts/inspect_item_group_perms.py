import os

import frappe

os.chdir("/home/frappe/frappe-bench/sites")
frappe.init(site="osscesariolange.erpnext.com")
frappe.connect()

configs = [
	("Material Request", "Material Request Item"),
	("Purchase Order", "Purchase Order Item"),
	("Purchase Receipt", "Purchase Receipt Item"),
	("Purchase Invoice", "Purchase Invoice Item"),
	("Request for Quotation", "Request for Quotation Item"),
	("Supplier Quotation", "Supplier Quotation Item"),
	("Stock Entry", "Stock Entry Detail"),
	("Delivery Note", "Delivery Note Item"),
	("Sales Order", "Sales Order Item"),
	("Sales Invoice", "Sales Invoice Item"),
	("Quotation", "Quotation Item"),
	("Pick List", "Pick List Item"),
	("Stock Reconciliation", "Stock Reconciliation Item"),
	("BOM", "BOM Item"),
	("Work Order", "Work Order Item"),
	("Asset Capitalization", "Asset Capitalization Stock Item"),
]

for parent, child in configs:
	if not frappe.db.exists("DocType", child):
		print(parent, child, "MISSING")
		continue
	meta = frappe.get_meta(child)
	fields = {f.fieldname for f in meta.fields}
	print(
		f"{child}: item_code={('item_code' in fields)} "
		f"item_group={('item_group' in fields)} item={('item' in fields)}"
	)

print("Item Group is_tree", frappe.get_meta("Item Group").is_tree)

# User permission structure sample from API
from frappe.permissions import get_user_permissions

# pick a non-admin user if any
users = frappe.get_all(
	"User Permission", fields=["user", "allow", "for_value"], limit=10
)
print("any UP samples", users)

frappe.destroy()
