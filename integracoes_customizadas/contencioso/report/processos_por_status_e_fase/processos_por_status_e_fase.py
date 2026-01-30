import frappe

from integracoes_customizadas.contencioso.utils import allowed_sigilo_levels


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"label": "Status", "fieldname": "cj_status", "fieldtype": "Data", "width": 120},
		{"label": "Fase", "fieldname": "cj_fase", "fieldtype": "Data", "width": 140},
		{"label": "Quantidade", "fieldname": "qtde", "fieldtype": "Int", "width": 120},
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

	conditions.append("cj_nivel_sigilo in %(sigilo)s")
	values["sigilo"] = allowed_sigilo

	if filters.get("company"):
		conditions.append("company = %(company)s")
		values["company"] = filters["company"]

	if filters.get("cj_tipo_processo"):
		conditions.append("cj_tipo_processo = %(cj_tipo_processo)s")
		values["cj_tipo_processo"] = filters["cj_tipo_processo"]

	if filters.get("data_inicio"):
		conditions.append("cj_data_distribuicao >= %(data_inicio)s")
		values["data_inicio"] = filters["data_inicio"]

	if filters.get("data_fim"):
		conditions.append("cj_data_distribuicao <= %(data_fim)s")
		values["data_fim"] = filters["data_fim"]

	where = " and ".join(conditions) if conditions else "1=1"
	query = f"""
		select
			cj_status,
			cj_fase,
			count(*) as qtde
		from `tabProcesso Judicial`
		where {where}
		group by cj_status, cj_fase
		order by cj_status asc, cj_fase asc
	"""

	return frappe.db.sql(query, values, as_dict=True)
