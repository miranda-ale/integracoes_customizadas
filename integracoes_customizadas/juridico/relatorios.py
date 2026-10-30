"""Apoio comum aos relatórios jurídicos de gestão (agrupamento e colunas)."""

from collections import defaultdict

from frappe import _
from frappe.utils import flt

CAMPOS_VALOR = (
	"valor_causa",
	"valor_condenacao",
	"valor_provisionado",
	"saldo_depositado",
	"total_acordos",
	"total_custas",
)


def coluna_moeda(fieldname, label, width=140):
	return {"fieldname": fieldname, "label": _(label), "fieldtype": "Currency", "width": width}


def coluna_texto(fieldname, label, width=140):
	return {"fieldname": fieldname, "label": _(label), "fieldtype": "Data", "width": width}


def agrupar(linhas, chaves, somas):
	"""Agrupa por `chaves` somando `somas`; devolve uma linha por grupo com `quantidade`."""
	grupos = defaultdict(lambda: defaultdict(float))
	rotulos = {}
	for linha in linhas:
		chave = tuple(linha.get(c) or _("(não informado)") for c in chaves)
		rotulos[chave] = dict(zip(chaves, chave, strict=True))
		grupos[chave]["quantidade"] += 1
		for soma in somas:
			grupos[chave][soma] += flt(linha.get(soma))
	return [{**rotulos[chave], **dict(valores)} for chave, valores in sorted(grupos.items())]


def passivo_liquido(linha):
	"""Provisão não coberta por depósitos (nunca negativa)."""
	return max(flt(linha.get("valor_provisionado")) - flt(linha.get("saldo_depositado")), 0)
