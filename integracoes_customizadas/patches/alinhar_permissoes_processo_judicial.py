"""Devolve as permissoes de Processo Judicial ao JSON do DocType e corrige o Role Profile juridico.

Havia Custom DocPerm so no banco (HR User com leitura/exportacao e System Manager com
permissoes extras) sobrepondo o JSON. O JSON passa a ser a unica fonte.
"""

import frappe

DOCTYPE = "Processo Judicial"
PERFIL = "Usuário Jurídico"
PAPEL_CORRETO = "Usuário Jurídico"
PAPEL_LEGADO = "CJ Analista Jurídico"


def execute():
	if frappe.db.exists("DocType", DOCTYPE):
		frappe.db.delete("Custom DocPerm", {"parent": DOCTYPE})
		frappe.clear_cache(doctype=DOCTYPE)
	_corrigir_role_profile()


def _corrigir_role_profile():
	if not (frappe.db.exists("Role Profile", PERFIL) and frappe.db.exists("Role", PAPEL_CORRETO)):
		return
	perfil = frappe.get_doc("Role Profile", PERFIL)
	papeis = [r.role for r in perfil.roles]
	if PAPEL_CORRETO in papeis and PAPEL_LEGADO not in papeis:
		return
	perfil.set(
		"roles",
		[{"role": r} for r in dict.fromkeys([PAPEL_CORRETO, *[p for p in papeis if p != PAPEL_LEGADO]])],
	)
	perfil.save(ignore_permissions=True)
