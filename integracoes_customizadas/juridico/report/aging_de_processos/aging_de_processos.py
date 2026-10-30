"""Aging: idade dos processos em andamento desde o ajuizamento, em faixas."""

from frappe.utils import date_diff, getdate, today

from integracoes_customizadas.juridico.relatorios import agrupar, coluna_moeda, coluna_texto
from integracoes_customizadas.juridico.report.relação_de_processos.relação_de_processos import listar_processos

FAIXAS = ((365, "Até 1 ano"), (730, "1 a 2 anos"), (1825, "2 a 5 anos"), (None, "Mais de 5 anos"))
CAMPOS = ["name", "empresa", "data_ajuizamento", "valor_causa", "valor_provisionado", "moeda"]


def faixa_de(dias):
	return next(rotulo for limite, rotulo in FAIXAS if limite is None or dias <= limite)


def execute(filters=None):
	linhas = listar_processos({**(filters or {}), "status_processo": "Em andamento"}, CAMPOS)
	for linha in linhas:
		dias = date_diff(today(), getdate(linha.data_ajuizamento)) if linha.data_ajuizamento else None
		linha["faixa"] = faixa_de(dias) if dias is not None else None
	data = agrupar(linhas, ("empresa", "faixa"), ("valor_causa", "valor_provisionado"))
	ordem = [rotulo for _limite, rotulo in FAIXAS]
	data.sort(key=lambda linha: (linha["empresa"], ordem.index(linha["faixa"]) if linha["faixa"] in ordem else len(ordem)))
	return get_columns(), data


def get_columns():
	return [
		coluna_texto("empresa", "Empresa", 200),
		coluna_texto("faixa", "Idade do Processo", 150),
		{"fieldname": "quantidade", "label": "Processos", "fieldtype": "Int", "width": 90},
		coluna_moeda("valor_causa", "Valor da Causa"),
		coluna_moeda("valor_provisionado", "Valor Provisionado"),
	]
