"""Conclui a limpeza do Contencioso: linhas orfas do ProcJud-2026-00001, DocTypes CJ * e tabelas soltas."""

import frappe

from integracoes_customizadas.patches import remover_contencioso_orfaos

TABELAS_LEGADAS = (
	"CJ Audiencia",
	"CJ Documento",
	"CJ Evento",
	"CJ Integracao",
	"CJ Item Financeiro",
	"CJ Parte",
	"CJ Prazo",
	"CJ Snapshot de Risco",
)


def execute():
	remover_contencioso_orfaos.execute()
	for nome in TABELAS_LEGADAS:
		if frappe.db.exists("DocType", nome) or not frappe.db.table_exists(nome):
			continue
		if frappe.db.count(nome):
			print(f"Contencioso: tabela {nome} mantida (possui dados)")
			continue
		frappe.db.sql_ddl(f"drop table `tab{nome}`")
