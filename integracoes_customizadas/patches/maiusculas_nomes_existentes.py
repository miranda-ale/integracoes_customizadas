import frappe

from integracoes_customizadas.normalizacao.maiusculas import CAMPOS, normalizar


def execute():
	"""Normaliza nomes já cadastrados. Não renomeia docnames (links); só lista os que divergem."""
	divergentes = []
	for doctype, campos in CAMPOS.items():
		meta = frappe.get_meta(doctype)
		campos = [c for c in campos if meta.has_field(c)]
		if not campos:
			continue
		for row in frappe.get_all(doctype, fields=["name", *campos]):
			novos = {c: normalizar(row[c]) for c in campos if row[c] and normalizar(row[c]) != row[c]}
			if novos:
				frappe.db.set_value(doctype, row["name"], novos, update_modified=False)
			if row["name"] != normalizar(row["name"]) and doctype in ("Company", "Supplier", "Customer"):
				divergentes.append(f"{doctype}: {row['name']}")
	if divergentes:
		print("Docnames mantidos (renomear é manual):\n" + "\n".join(divergentes))
