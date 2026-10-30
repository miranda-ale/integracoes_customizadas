"""Provisão dos processos por empresa, risco e probabilidade de perda."""

from integracoes_customizadas.juridico.relatorios import agrupar, coluna_moeda, coluna_texto, passivo_liquido
from integracoes_customizadas.juridico.report.relação_de_processos.relação_de_processos import listar_processos

CAMPOS = ["name", "empresa", "moeda", "risco", "probabilidade_perda", "valor_causa", "valor_provisionado", "saldo_depositado", "total_acordos", "total_custas"]
SOMAS = ("valor_causa", "valor_provisionado", "saldo_depositado", "total_acordos", "passivo_liquido")


def execute(filters=None):
	linhas = listar_processos(filters, CAMPOS)
	for linha in linhas:
		linha["passivo_liquido"] = passivo_liquido(linha)
	data = agrupar(linhas, ("empresa", "risco", "probabilidade_perda"), SOMAS)
	return get_columns(), data


def get_columns():
	return [
		coluna_texto("empresa", "Empresa", 200),
		coluna_texto("risco", "Risco", 90),
		coluna_texto("probabilidade_perda", "Probabilidade de Perda", 150),
		{"fieldname": "quantidade", "label": "Processos", "fieldtype": "Int", "width": 90},
		coluna_moeda("valor_causa", "Valor da Causa"),
		coluna_moeda("valor_provisionado", "Valor Provisionado"),
		coluna_moeda("saldo_depositado", "Saldo Depositado"),
		coluna_moeda("total_acordos", "Acordos"),
		coluna_moeda("passivo_liquido", "Passivo Líquido"),
	]
