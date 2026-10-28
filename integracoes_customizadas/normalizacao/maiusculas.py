"""Nomes de cadastro sempre em CAIXA ALTA e sem acento (padrão estético dos cadastros)."""

import re
import unicodedata

import frappe

# DocType -> campos de nome. Allowlist explícita: evita atingir e-mail, User.full_name etc.
CAMPOS = {
	"Employee": ["first_name", "middle_name", "last_name", "employee_name"],
	"Company": ["company_name"],
	"Supplier": ["supplier_name"],
	"Customer": ["customer_name"],
	"Item": ["item_name"],
	"Contact": ["first_name", "middle_name", "last_name"],
	"Address": ["address_title"],
	"Lead": ["lead_name", "first_name", "middle_name", "last_name", "company_name"],
	"Department": ["department_name"],
	"Designation": ["designation_name"],
}


def normalizar(valor):
	"""Sem diacríticos, em maiúsculas e com espaços colapsados."""
	if not isinstance(valor, str):
		return valor
	sem_acento = "".join(c for c in unicodedata.normalize("NFKD", valor) if not unicodedata.combining(c))
	return re.sub(r"\s+", " ", sem_acento).strip().upper()


def aplicar(doc, method=None):
	campos = CAMPOS.get(doc.doctype)
	if not campos:
		return
	meta = frappe.get_meta(doc.doctype)
	for campo in campos:
		if meta.has_field(campo) and doc.get(campo):
			doc.set(campo, normalizar(doc.get(campo)))
