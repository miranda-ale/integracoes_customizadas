# Copyright (c) 2026, BHCL and contributors
# For license information, please see license.txt
"""Nota Fiscal registrada no Purchase Receipt pela unidade que recebe (campos `custom_compras_nf_*`).

A chave de acesso é validada (44 posições + dígito verificador módulo 11); divergências de número, de fornecedor
e de valor apenas avisam, porque a NF pode trazer frete/IPI que o recebimento não tem. A Purchase Invoice herda
número e data da NF do recebimento de origem.
"""

import re

import frappe
from frappe.utils import flt

CHAVE_RE = re.compile(r"^[0-9A-Z]{44}$")


def normalizar_chave(chave):
	"""Remove espaços e pontuação; mantém dígitos e letras (CNPJ alfanumérico)."""
	return re.sub(r"[^0-9A-Za-z]", "", chave or "").upper()


def digito_verificador(base43):
	"""DV módulo 11 da chave de acesso (pesos 2..9 da direita para a esquerda; letras valem ord - 48)."""
	soma = 0
	for i, c in enumerate(reversed(base43)):
		soma += (ord(c) - 48) * (2 + i % 8)
	resto = soma % 11
	return 0 if resto in (0, 1) else 11 - resto


def chave_valida(chave):
	return (
		bool(CHAVE_RE.match(chave))
		and chave[-1].isdigit()
		and digito_verificador(chave[:43]) == int(chave[-1])
	)


def decompor_chave(chave):
	"""Partes da chave: UF, AAMM, CNPJ emitente, modelo, série e número da NF."""
	return {
		"uf": chave[0:2],
		"aamm": chave[2:6],
		"cnpj": chave[6:20],
		"modelo": chave[20:22],
		"serie": chave[22:25],
		"numero": chave[25:34],
	}


def _so_alnum(valor):
	return re.sub(r"[^0-9A-Za-z]", "", valor or "").upper()


def validar_nota_fiscal(doc, method=None):
	"""validate / before_update_after_submit do Purchase Receipt."""
	chave = normalizar_chave(doc.get("custom_compras_nf_chave"))
	if chave:
		if not chave_valida(chave):
			frappe.throw(
				"A Chave de Acesso da NF é inválida: informe as 44 posições (o dígito verificador não confere).",
				title="Nota Fiscal",
			)
		doc.custom_compras_nf_chave = chave
		partes = decompor_chave(chave)
		if not doc.get("custom_compras_nf_numero"):
			doc.custom_compras_nf_numero = str(int(partes["numero"])) if partes["numero"].isdigit() else ""
		elif partes["numero"].isdigit() and _so_alnum(doc.custom_compras_nf_numero).lstrip("0") != str(
			int(partes["numero"])
		):
			frappe.msgprint(
				f"O número da NF ({doc.custom_compras_nf_numero}) difere do número contido na chave "
				f"({int(partes['numero'])}).",
				indicator="orange",
				title="Nota Fiscal",
			)
		if not doc.get("custom_compras_nf_serie") and partes["serie"].isdigit():
			doc.custom_compras_nf_serie = str(int(partes["serie"]))
		_avisar_fornecedor(doc, partes["cnpj"])
	_avisar_valor(doc)


def _avisar_fornecedor(doc, cnpj_chave):
	tax_id = _so_alnum(frappe.db.get_value("Supplier", doc.supplier, "tax_id")) if doc.supplier else ""
	# Supplier.tax_id is not always clean: only compare when it looks like a CNPJ.
	if len(tax_id) == 14 and tax_id != cnpj_chave:
		frappe.msgprint(
			"O CNPJ do emitente da NF (chave de acesso) não corresponde ao CNPJ do fornecedor do recebimento.",
			indicator="orange",
			title="Nota Fiscal",
		)


def _avisar_valor(doc):
	nf_valor = flt(doc.get("custom_compras_nf_valor"))
	total = flt(doc.get("grand_total"))
	if nf_valor and abs(nf_valor - total) > max(1.0, total * 0.005):
		frappe.msgprint(
			f"O valor da NF ({frappe.format_value(nf_valor, {'fieldtype': 'Currency'})}) difere do total "
			f"recebido ({frappe.format_value(total, {'fieldtype': 'Currency'})}). Confira antes de faturar.",
			indicator="orange",
			title="Nota Fiscal",
		)


def herdar_nota_fiscal(doc, method=None):
	"""before_validate da Purchase Invoice: usa número e data da NF do recebimento de origem, se único."""
	if doc.get("bill_no"):
		return
	recebimentos = {i.purchase_receipt for i in doc.get("items") or [] if i.get("purchase_receipt")}
	if len(recebimentos) != 1:
		return
	numero, data = frappe.db.get_value(
		"Purchase Receipt",
		recebimentos.pop(),
		["custom_compras_nf_numero", "custom_compras_nf_data"],
	) or (None, None)
	if numero:
		doc.bill_no = numero
		if data and not doc.get("bill_date"):
			doc.bill_date = data
