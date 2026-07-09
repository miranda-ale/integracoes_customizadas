from __future__ import annotations

import frappe
from frappe.permissions import get_user_permissions

DOC_ITEM_MAP: dict[str, tuple[str, str, str, bool]] = {
	"Material Request": ("Material Request Item", "items", "item_code", True),
	"Request for Quotation": ("Request for Quotation Item", "items", "item_code", True),
	"Supplier Quotation": ("Supplier Quotation Item", "items", "item_code", True),
	"Purchase Order": ("Purchase Order Item", "items", "item_code", True),
	"Purchase Receipt": ("Purchase Receipt Item", "items", "item_code", True),
	"Purchase Invoice": ("Purchase Invoice Item", "items", "item_code", True),
	"Quotation": ("Quotation Item", "items", "item_code", True),
	"Sales Order": ("Sales Order Item", "items", "item_code", True),
	"Delivery Note": ("Delivery Note Item", "items", "item_code", True),
	"Sales Invoice": ("Sales Invoice Item", "items", "item_code", True),
	"Stock Entry": ("Stock Entry Detail", "items", "item_code", True),
	"Pick List": ("Pick List Item", "locations", "item_code", True),
	"Stock Reconciliation": ("Stock Reconciliation Item", "items", "item_code", True),
	"BOM": ("BOM Item", "items", "item_code", False),
	"Work Order": ("Work Order Item", "required_items", "item_code", False),
	"Asset Capitalization": (
		"Asset Capitalization Stock Item",
		"stock_items",
		"item_code",
		False,
	),
}

def get_allowed_item_groups(user: str | None, doctype: str) -> list[str] | None:
	user = user or frappe.session.user
	if not user or user in ("Administrator", "Guest"):
		return None

	child_doctype = DOC_ITEM_MAP[doctype][0] if doctype in DOC_ITEM_MAP else None

	perms = get_user_permissions(user).get("Item Group") or []
	if not perms:
		return None

	allowed: list[str] = []
	relevant = False
	for p in perms:
		app_for = p.get("applicable_for") or None
		if not app_for or app_for in (doctype, child_doctype, "Item", "Item Group"):
			relevant = True
			docname = p.get("doc")
			if docname:
				allowed.append(docname)

	if not relevant:
		return None

	return list(dict.fromkeys(allowed))

def _sql_in_list(values: list[str]) -> str:
	if not values:
		return "(NULL)"
	return "(" + ", ".join(frappe.db.escape(v) for v in values) + ")"

def build_item_group_query_condition(user: str | None, doctype: str) -> str:
	if doctype not in DOC_ITEM_MAP:
		return ""

	allowed = get_allowed_item_groups(user, doctype)
	if allowed is None:
		return ""
	if not allowed:
		return "1=0"

	child_doctype, _parentfield, item_code_field, has_ig = DOC_ITEM_MAP[doctype]
	parent_table = f"`tab{doctype}`"
	child_table = f"`tab{child_doctype}`"
	in_list = _sql_in_list(allowed)
	parenttype_sql = frappe.db.escape(doctype)

	if has_ig:
		disallowed_exists = f"""
			EXISTS (
				SELECT 1
				FROM {child_table} _ig_child
				LEFT JOIN `tabItem` _ig_item
					ON _ig_item.name = _ig_child.`{item_code_field}`
				WHERE _ig_child.parent = {parent_table}.name
					AND IFNULL(_ig_child.parenttype, {parenttype_sql}) = {parenttype_sql}
					AND IFNULL(_ig_child.`{item_code_field}`, '') != ''
					AND COALESCE(
						NULLIF(_ig_child.item_group, ''),
						_ig_item.item_group,
						''
					) != ''
					AND COALESCE(
						NULLIF(_ig_child.item_group, ''),
						_ig_item.item_group,
						''
					) NOT IN {in_list}
			)
			EXISTS (
				SELECT 1
				FROM {child_table} _ig_child
				INNER JOIN `tabItem` _ig_item
					ON _ig_item.name = _ig_child.`{item_code_field}`
				WHERE _ig_child.parent = {parent_table}.name
					AND IFNULL(_ig_child.parenttype, {parenttype_sql}) = {parenttype_sql}
					AND IFNULL(_ig_child.`{item_code_field}`, '') != ''
					AND IFNULL(_ig_item.item_group, '') != ''
					AND _ig_item.item_group NOT IN {in_list}
			)
	Hook signature (Frappe v15 db_query):
	  frappe.call(method, self.user, doctype=self.doctype)
	Hook signature:
	  frappe.call(method, doc=doc, ptype=ptype, user=user, debug=debug)

	False = negar | None = continuar fluxo padrao (nunca retornar True).
	"""
	if doc is None:
		return None

	doctype = getattr(doc, "doctype", None)
	if not doctype and hasattr(doc, "get"):
		doctype = doc.get("doctype")
	if not doctype or doctype not in DOC_ITEM_MAP:
		return None

	user = user or frappe.session.user
	allowed = get_allowed_item_groups(user, doctype)
	if allowed is None:
		return None

	allowed_set = set(allowed)
	_child_doctype, parentfield, item_code_field, has_ig = DOC_ITEM_MAP[doctype]

	rows = []
	if hasattr(doc, "get"):
		rows = doc.get(parentfield) or []

	is_new = False
	if hasattr(doc, "is_new"):
		try:
			is_new = bool(doc.is_new())
		except Exception:
			is_new = False

	if not rows and getattr(doc, "name", None) and not is_new:
		fields = [item_code_field]
		if has_ig:
			fields.append("item_group")
		rows = frappe.get_all(
			_child_doctype,
			filters={"parent": doc.name, "parenttype": doctype},
			fields=fields,
		)

	for row in rows:
		if hasattr(row, "get"):
			item_code = row.get(item_code_field)
			item_group = row.get("item_group") if has_ig else None
		else:
			item_code = getattr(row, item_code_field, None)
			item_group = getattr(row, "item_group", None) if has_ig else None

		if not item_code:
			continue

		if not item_group:
			item_group = frappe.db.get_value("Item", item_code, "item_group")

		if item_group and item_group not in allowed_set:
			return False

	return None
