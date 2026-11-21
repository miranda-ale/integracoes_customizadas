# Copyright (c) 2026, Alessandro Miranda and contributors
# For license information, please see license.txt
"""DocTypes de cadastro que em produção foram criados pela interface e que o app passa a instalar.

Os Custom Fields de `Employee`/`Designation` (fixtures do app) e o card Ética do workspace Jurídico apontam para
`Municipios`, `CBO`, `Dependentes` e `Canal de Denuncias` (este usa a tabela `Colaboradores Link`). As definições
em `definicoes/*.json` foram extraídas do site de produção (campos, opções, nomeação e permissões), sem dados.

Regras de segurança para produção:
- só cria o DocType que NÃO existe (nunca atualiza campos, nomeação nem permissões de um site que já o tem);
- por isso os JSON ficam fora de `<módulo>/doctype/`, que o `migrate` sincroniza por cima do que existe;
- os DocTypes são `custom=1` e mantêm o módulo de produção ("HR", "Gestor Online"), para o nome do módulo não mudar;
- as permissões são exatamente as de produção; papel que ainda não existe no site é ignorado (não é criado).
Roda em `after_install` e `after_migrate`, na ordem em que as dependências exigem (tabela filha antes do pai).
"""

from __future__ import annotations

import json
from pathlib import Path

import frappe

DEFINICOES_DIR = Path(__file__).resolve().parent / "definicoes"
# Ordem de criação: `Colaboradores Link` é a tabela usada por `Canal de Denuncias`.
ARQUIVOS = ("cbo", "municipios", "dependentes", "colaboradores_link", "canal_de_denuncias")


def carregar_definicao(arquivo: str) -> dict:
	return json.loads((DEFINICOES_DIR / f"{arquivo}.json").read_text(encoding="utf-8"))


def _garantir_modulo(modulo: str):
	if not frappe.db.exists("Module Def", modulo):
		frappe.get_doc({"doctype": "Module Def", "module_name": modulo, "custom": 1}).insert(
			ignore_permissions=True
		)


def garantir_doctype(definicao: dict) -> bool:
	"""Cria o DocType se ele não existir; devolve True quando criou. Nunca altera um existente."""
	nome = definicao["name"]
	if frappe.db.exists("DocType", nome):
		return False
	doc = {k: v for k, v in definicao.items() if k != "permissions"}
	doc["permissions"] = [p for p in definicao.get("permissions", []) if frappe.db.exists("Role", p["role"])]
	_garantir_modulo(doc["module"])
	frappe.get_doc(doc).insert(ignore_permissions=True)
	return True


def garantir_cadastros() -> list[str]:
	criados = []
	for arquivo in ARQUIVOS:
		definicao = carregar_definicao(arquivo)
		if garantir_doctype(definicao):
			criados.append(definicao["name"])
	if criados:
		frappe.clear_cache()
	return criados
