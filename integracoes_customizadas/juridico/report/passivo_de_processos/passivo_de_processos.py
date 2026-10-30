"""Passivo por processo: provisão, depósitos, acordos, custas e passivo líquido."""

from integracoes_customizadas.juridico.relatorios import coluna_moeda, coluna_texto, passivo_liquido
from integracoes_customizadas.juridico.report.relação_de_processos.relação_de_processos import listar_processos

CAMPOS = ["numero_processo", "nome_parte", "natureza", "data_provisao", "resultado", "name", "empresa", "moeda", "risco", "probabilidade_perda", "valor_causa", "valor_provisionado", "saldo_depositado", "total_acordos", "total_custas"]


def execute(filters=None):
	data = listar_processos(filters, CAMPOS)
	for linha in data:
		linha["passivo_liquido"] = passivo_liquido(linha)
	return get_columns(), data


def get_columns():
	return [
		coluna_texto("numero_processo", "Número do Processo", 195),
		coluna_texto("empresa", "Empresa", 180),
		coluna_texto("nome_parte", "Parte", 180),
		coluna_texto("natureza", "Natureza", 100),
		coluna_texto("risco", "Risco", 80),
		coluna_texto("probabilidade_perda", "Probabilidade", 110),
		coluna_moeda("valor_causa", "Valor da Causa"),
		coluna_moeda("valor_provisionado", "Valor Provisionado"),
		coluna_moeda("saldo_depositado", "Saldo Depositado"),
		coluna_moeda("total_acordos", "Acordos"),
		coluna_moeda("total_custas", "Custas"),
		coluna_moeda("passivo_liquido", "Passivo Líquido"),
	]
