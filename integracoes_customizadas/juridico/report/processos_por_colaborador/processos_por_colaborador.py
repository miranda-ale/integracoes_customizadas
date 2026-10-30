"""Processos por unidade e cargo: dados do Employee quando há vínculo, do processo quando não há."""

import frappe

from integracoes_customizadas.juridico.relatorios import agrupar, coluna_moeda, coluna_texto
from integracoes_customizadas.juridico.report.relação_de_processos.relação_de_processos import listar_processos

CAMPOS = ["name", "parte", "nome_parte", "cargo_funcao", "valor_causa", "valor_provisionado", "moeda"]


def execute(filters=None):
	linhas = listar_processos({**(filters or {}), "tipo_parte": "Employee"}, CAMPOS)
	colaboradores = {
		e.name: e
		for e in frappe.get_all(
			"Employee",
			filters={"name": ["in", [linha.parte for linha in linhas if linha.parte] or [""]]},
			fields=["name", "branch", "designation"],
		)
	}
	for linha in linhas:
		colaborador = colaboradores.get(linha.parte)
		linha["unidade"] = colaborador.branch if colaborador else None
		linha["cargo"] = (colaborador.designation if colaborador else None) or linha.cargo_funcao
	data = agrupar(linhas, ("unidade", "cargo"), ("valor_causa", "valor_provisionado"))
	return get_columns(), data


def get_columns():
	return [
		coluna_texto("unidade", "Unidade", 200),
		coluna_texto("cargo", "Cargo/Função", 200),
		{"fieldname": "quantidade", "label": "Processos", "fieldtype": "Int", "width": 90},
		coluna_moeda("valor_causa", "Valor da Causa"),
		coluna_moeda("valor_provisionado", "Valor Provisionado"),
	]
