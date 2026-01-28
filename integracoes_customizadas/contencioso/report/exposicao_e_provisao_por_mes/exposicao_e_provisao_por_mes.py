import frappe
from frappe.utils import formatdate

from integracoes_customizadas.contencioso.utils import allowed_sigilo_levels


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"label": "Competência", "fieldname": "competencia", "fieldtype": "Data", "width": 100},
		{"label": "Empresa", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 160},
		{"label": "Valor do Pedido", "fieldname": "cj_valor_pedido", "fieldtype": "Currency", "width": 140},
		{"label": "Valor Estimado", "fieldname": "cj_valor_estimado", "fieldtype": "Currency", "width": 140},
		{"label": "Provisão Atual", "fieldname": "cj_provisao_atual", "fieldtype": "Currency", "width": 140},
		{"label": "Delta Provisão Mês Anterior", "fieldname": "delta_provisao", "fieldtype": "Currency", "width": 180},
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

	where = " and ".join(conditions) if conditions else "1=1"
	query = f"""
		select
			date_format(ifnull(cj_data_distribuicao, creation), '%%Y-%%m') as competencia,
			company,
			sum(ifnull(cj_valor_pedido, 0)) as cj_valor_pedido,
			sum(ifnull(cj_valor_estimado, 0)) as cj_valor_estimado,
			sum(ifnull(cj_provisao_atual, 0)) as cj_provisao_atual
		from `tabProcesso Judicial`
		where {where}
		group by competencia, company
		order by competencia asc, company asc
	"""

	rows = frappe.db.sql(query, values, as_dict=True)
	prev_by_company = {}
	for row in rows:
		key = row["company"]
		prev = prev_by_company.get(key)
		row["delta_provisao"] = (row["cj_provisao_atual"] - prev) if prev is not None else 0
		prev_by_company[key] = row["cj_provisao_atual"]
		row["competencia"] = formatdate(f"{row['competencia']}-01")
	return rows
