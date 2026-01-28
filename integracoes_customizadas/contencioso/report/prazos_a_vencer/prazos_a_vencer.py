import frappe
from frappe.utils import add_days, today

from integracoes_customizadas.contencioso.utils import allowed_sigilo_levels, mask_cpf_cnpj


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"label": "Processo", "fieldname": "processo", "fieldtype": "Link", "options": "Processo Judicial", "width": 180},
		{"label": "CNJ", "fieldname": "cj_numero_cnj", "fieldtype": "Data", "width": 140},
		{"label": "Tipo do Prazo", "fieldname": "cj_tipo_prazo", "fieldtype": "Data", "width": 140},
		{"label": "Data de Vencimento", "fieldname": "cj_data_vencimento", "fieldtype": "Date", "width": 130},
		{"label": "Responsável", "fieldname": "responsavel", "fieldtype": "Link", "options": "User", "width": 140},
		{"label": "Status do Prazo", "fieldname": "cj_status_prazo", "fieldtype": "Data", "width": 120},
		{"label": "Nível de Sigilo", "fieldname": "cj_nivel_sigilo", "fieldtype": "Data", "width": 120},
	]

	data = _get_data(filters)
	return columns, data


def _get_data(filters):
	conditions = []
	values = {}

	allowed_sigilo = allowed_sigilo_levels()
	if filters.get("cj_nivel_sigilo"):
		if filters["cj_nivel_sigilo"] in allowed_sigilo:
			allowed_sigilo = [filters["cj_nivel_sigilo"]]
		else:
			return []

	conditions.append("pj.cj_nivel_sigilo in %(sigilo)s")
	values["sigilo"] = allowed_sigilo

	if filters.get("company"):
		conditions.append("pj.company = %(company)s")
		values["company"] = filters["company"]

	if filters.get("cj_status_prazo"):
		conditions.append("pp.cj_status_prazo = %(cj_status_prazo)s")
		values["cj_status_prazo"] = filters["cj_status_prazo"]

	start = filters.get("data_inicio") or today()
	end = filters.get("data_fim") or add_days(today(), 30)
	conditions.append("pp.cj_data_vencimento between %(data_inicio)s and %(data_fim)s")
	values["data_inicio"] = start
	values["data_fim"] = end

	if filters.get("responsavel"):
		conditions.append("(pp.cj_responsavel_usuario = %(responsavel)s or pj.cj_responsavel_usuario = %(responsavel)s)")
		values["responsavel"] = filters["responsavel"]

	where = " and ".join(conditions) if conditions else "1=1"

	query = f"""
		select
			pp.parent as processo,
			pj.cj_numero_cnj,
			pp.cj_tipo_prazo,
			pp.cj_data_vencimento,
			coalesce(pp.cj_responsavel_usuario, pj.cj_responsavel_usuario) as responsavel,
			pp.cj_status_prazo,
			pj.cj_nivel_sigilo
		from `tabCJ Prazo` pp
		inner join `tabProcesso Judicial` pj on pj.name = pp.parent
		where {where}
		order by pp.cj_data_vencimento asc
	"""

	rows = frappe.db.sql(query, values, as_dict=True)
	for row in rows:
		row["cj_numero_cnj"] = mask_cpf_cnpj(row["cj_numero_cnj"])
	return rows
