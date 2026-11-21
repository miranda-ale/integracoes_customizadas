# Copyright (c) 2026, BHCL and contributors
# For license information, please see license.txt
"""Rótulos da cadeia de compras que ESTE app cria nascem em português.

A tradução dos rótulos do ERPNext (Tax Withholding, Apply TDS etc.) é do `bhcl_theme` (dono único das traduções
pt/pt-BR do grupo, em `bhcl_theme/translations/pt*.csv`); este app não tem arquivo de tradução. O teste cobre só
o que o app possui: os Custom Fields `custom_compras_*` (`compras/setup.py`) e os campos Bionexo.
"""

from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

from integracoes_customizadas.compras.setup import NF_FIELDS

CAMPOS_BIONEXO = {
	("Request for Quotation", "custom_id_bionexo"): "ID Bionexo",
	("Request for Quotation", "custom_link_bionexo"): "Link Bionexo",
	("Item", "custom_código_bionexo"): "Código Bionexo",
}


class TestTraducoesCompras(FrappeTestCase):
	def test_rotulos_criados_pelo_app_estao_em_portugues(self):
		esperados = {
			(doctype, df["fieldname"]): df["label"]
			for doctype, campos in NF_FIELDS.items()
			for df in campos
			if df.get("label")
		}
		esperados.update(CAMPOS_BIONEXO)
		divergentes = {}
		for (doctype, fieldname), label in esperados.items():
			campo = frappe.get_meta(doctype).get_field(fieldname)
			atual = campo.label if campo else None
			if atual != label:
				divergentes[f"{doctype}.{fieldname}"] = atual
		self.assertEqual(divergentes, {}, "Rótulos do app ausentes ou diferentes do definido em português.")

	def test_app_nao_tem_arquivos_de_traducao(self):
		# O dono das traduções é o bhcl_theme; um arquivo aqui voltaria a duplicar a fonte.
		pasta = Path(frappe.get_app_path("integracoes_customizadas")) / "translations"
		self.assertEqual(list(pasta.glob("*.csv")) if pasta.exists() else [], [])
