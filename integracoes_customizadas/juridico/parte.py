"""Vínculo posterior de processos judiciais a colaboradores cadastrados."""

import frappe
from frappe import _

from busca_cnpj.cnpj import validar_cpf


def _campo_cpf_employee() -> str | None:
	"""Campo de CPF do Employee (criado pelo app rh_brasil)."""
	return "custom_cpf" if frappe.get_meta("Employee").has_field("custom_cpf") else None


def _employee_por_cpf(cpf: str, campo: str) -> str | None:
	digitos = "".join(c for c in cpf if c.isdigit())
	if not validar_cpf(digitos):
		return None
	encontrados = frappe.db.sql(
		f"""select name from `tabEmployee`
		where replace(replace(replace(`{campo}`, '.', ''), '-', ''), ' ', '') = %s
		limit 2""",
		digitos,
	)
	# Mais de um resultado é ambíguo (ex.: recontratação); não vincula automaticamente.
	return encontrados[0][0] if len(encontrados) == 1 else None


@frappe.whitelist()
def vincular_colaborador(processo: str) -> dict:
	"""Procura o Employee pelo CPF da parte e vincula ao processo."""
	doc = frappe.get_doc("Processo Judicial", processo)
	doc.check_permission("write")
	if doc.parte:
		return {"vinculado": False, "motivo": _("O processo já possui parte vinculada.")}
	campo = _campo_cpf_employee()
	if not (doc.cpf_parte and campo):
		return {"vinculado": False, "motivo": _("Informe o CPF da parte para buscar o colaborador.")}
	employee = _employee_por_cpf(doc.cpf_parte, campo)
	if not employee:
		return {"vinculado": False, "motivo": _("Nenhum colaborador único encontrado para o CPF.")}
	# A tabela é a fonte da parte; o save espelha a principal nos campos de topo.
	principal = next((linha for linha in doc.partes if linha.principal), None)
	for destino in (doc, principal) if principal else (doc,):
		destino.tipo_parte = "Employee"
		destino.parte = employee
	doc.save()
	return {"vinculado": True, "employee": employee}


@frappe.whitelist()
def vincular_em_lote() -> dict:
	"""Reconcilia todos os processos sem vínculo cujo CPF corresponda a um único Employee."""
	frappe.only_for(("Usuário Jurídico", "System Manager"))
	pendentes = frappe.get_all(
		"Processo Judicial",
		filters={"parte_vinculada": 0, "cpf_parte": ["is", "set"], "tipo_parte": ["in", ["Employee", ""]]},
		pluck="name",
	)
	vinculados = sum(1 for nome in pendentes if vincular_colaborador(nome)["vinculado"])
	return {"analisados": len(pendentes), "vinculados": vinculados}
