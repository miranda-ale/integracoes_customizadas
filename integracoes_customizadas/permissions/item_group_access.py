"""
Restringe List View / get_list de documentos de item pela User Permission de Item Group.

Problema:
  User Permission em Item Group filtra Link fields (Item), mas a List View de
  Material Request / Purchase Order / etc. nao herda esse filtro via child table.
  O usuario ve documentos que nao consegue abrir.

Solucao (padrao Frappe):
  - permission_query_conditions: SQL no backend (get_list / List View)
  - has_permission: reforca a mesma regra na abertura do documento

Regra:
  Se o usuario tem User Permission de Item Group aplicavel ao DocType, so ve
  documentos cujos itens (todos) pertencem a grupos permitidos.
  Documentos com qualquer item fora dos grupos permitidos ficam ocultos.
"""

from __future__ import annotations

import frappe
from frappe.permissions import get_user_permissions

# parent_doctype -> (child_doctype, parentfield, item_code_field, has_item_group_on_child)
DOC_ITEM_MAP: dict[str, tuple[str, str, str, bool]] = {
	# Buying
	"Material Request": ("Material Request Item", "items", "item_code", True),
	"Request for Quotation": ("Request for Quotation Item", "items", "item_code", True),
	"Supplier Quotation": ("Supplier Quotation Item", "items", "item_code", True),
	"Purchase Order": ("Purchase Order Item", "items", "item_code", True),
	"Purchase Receipt": ("Purchase Receipt Item", "items", "item_code", True),
	"Purchase Invoice": ("Purchase Invoice Item", "items", "item_code", True),
	# Selling
	"Quotation": ("Quotation Item", "items", "item_code", True),
	"Sales Order": ("Sales Order Item", "items", "item_code", True),
	"Delivery Note": ("Delivery Note Item", "items", "item_code", True),
	"Sales Invoice": ("Sales Invoice Item", "items", "item_code", True),
	# Stock
	"Stock Entry": ("Stock Entry Detail", "items", "item_code", True),
	"Pick List": ("Pick List Item", "locations", "item_code", True),
	"Stock Reconciliation": ("Stock Reconciliation Item", "items", "item_code", True),
	# Manufacturing
	"BOM": ("BOM Item", "items", "item_code", False),
	"Work Order": ("Work Order Item", "required_items", "item_code", False),
	# Assets
	"Asset Capitalization": (
		"Asset Capitalization Stock Item",
		"stock_items",
		"item_code",
		False,
	),
}


def get_allowed_item_groups(user: str | None, doctype: str) -> list[str] | None:
	"""
	Retorna lista de Item Groups permitidos se o usuario esta restrito.
	Retorna None se nao ha restricao de Item Group para este DocType.
	"""
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
		# applicable_for vazio = apply to all doctypes
		if not app_for or app_for in (doctype, child_doctype, "Item", "Item Group"):
			relevant = True
			docname = p.get("doc")
			if docname:
				allowed.append(docname)

	if not relevant:
		return None

	# remove duplicatas preservando ordem (descendants ja vem expandidos do core)
	return list(dict.fromkeys(allowed))


def _sql_in_list(values: list[str]) -> str:
	if not values:
		return "(NULL)"
	return "(" + ", ".join(frappe.db.escape(v) for v in values) + ")"


def build_item_group_query_condition(user: str | None, doctype: str) -> str:
	"""SQL fragment for permission_query_conditions (sem AND/WHERE inicial)."""
	if doctype not in DOC_ITEM_MAP:
		return ""

	allowed = get_allowed_item_groups(user, doctype)
	if allowed is None:
		return ""
	if not allowed:
		# Restrito a Item Group, mas sem nenhum valor permitido - nada a listar
		return "1=0"

	child_doctype, _parentfield, item_code_field, has_ig = DOC_ITEM_MAP[doctype]
	parent_table = f"`tab{doctype}`"
	child_table = f"`tab{child_doctype}`"
	in_list = _sql_in_list(allowed)
	parenttype_sql = frappe.db.escape(doctype)

	# Documento permitido se NAO existe linha com item_group fora da lista permitida.
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
		"""
	else:
		disallowed_exists = f"""
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
		"""

	return f"(NOT {disallowed_exists})"


def permission_query_conditions(user: str | None = None, doctype: str | None = None) -> str:
	"""
	Hook signature (Frappe v15 db_query):
	  frappe.call(method, self.user, doctype=self.doctype)
	"""
	user = user or frappe.session.user
	if not doctype:
		return ""

	try:
		return build_item_group_query_condition(user, doctype) or ""
	except Exception:
		frappe.log_error(
			title="item_group_access.permission_query_conditions",
			message=frappe.get_traceback(),
		)
		# fail-closed se o usuario e restrito
		try:
			if get_allowed_item_groups(user, doctype) is not None:
				return "1=0"
		except Exception:
			pass
		return ""


def has_permission(doc=None, ptype: str | None = None, user: str | None = None, **kwargs) -> bool | None:
	"""
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

	# Checagem por nome sem child em memoria
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
