# Copyright (c) 2026, StillPulse Tecnologia LTDA and contributors
# For license information, please see license.txt
"""Rótulos da cadeia de compras sem tradução pt-BR (o cliente busca a chave exata, inclusive espaço no fim)."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.translate import get_all_translations

DOCTYPES = (
	"Material Request",
	"Material Request Item",
	"Request for Quotation",
	"Request for Quotation Item",
	"Supplier Quotation",
	"Supplier Quotation Item",
	"Purchase Order",
	"Purchase Order Item",
	"Purchase Receipt",
	"Purchase Receipt Item",
	"Purchase Invoice",
	"Purchase Invoice Item",
	"Purchase Taxes and Charges",
)
# Iguais em português ou já escritos em português nos Custom Fields do site.
PERMITIDOS = frozenset(
	{
		"Total",
		"Status",
		"Incoterm",
		"Item",
		"Série",
		"Valor Total",
		"Valor Unitário",
		"ID Bionexo",
		"Link Bionexo",
		"Processo 1Doc",
		"Dados do Paciente",
		"Categoria da Compra",
		"Definir Armazém de Destino",
		"Número da Cotação / Proposta",
		"Endereço de Faturamento da Empresa",
		"Detalhes Endereço de Faturamento da Empresa",
	}
)


class TestTraducoesCompras(FrappeTestCase):
	def test_rotulos_da_cadeia_estao_em_portugues(self):
		# The pt-BR labels of ERPNext's fields live in bhcl_theme/translations (a site-wide theme app, not a dependency of
		# this app): without it installed there is nothing to check here.
		if "bhcl_theme" not in frappe.get_installed_apps():
			self.skipTest("bhcl_theme (owner of the ERPNext pt-BR labels) is not installed on this site")
		traducoes = get_all_translations("pt-BR")
		faltando = {}
		for doctype in DOCTYPES:
			for campo in frappe.get_meta(doctype).fields:
				label = campo.label
				if not label or campo.fieldtype == "HTML" or len(label.strip()) <= 2:
					continue
				if label in PERMITIDOS or label.startswith("Nota Fiscal") or label in traducoes:
					continue
				# Rótulos que o próprio app cria já nascem em português (custom_compras_*).
				if campo.fieldname.startswith("custom_compras_"):
					continue
				faltando.setdefault(doctype, []).append(label)
		self.assertEqual(
			faltando, {}, "Rótulos sem tradução pt-BR: acrescente-os a bhcl_theme/translations/pt*.csv."
		)
