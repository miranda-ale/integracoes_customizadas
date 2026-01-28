import frappe
from frappe.utils import formatdate

from integracoes_customizadas.contencioso.utils import allowed_sigilo_levels


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"label": "Competência", "fieldname": "competencia", "fieldtype": "Data", "width": 100},
		{"label": "Empresa", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 160},
		{"label": "Tipo Financeiro", "fieldname": "cj_tipo", "fieldtype": "Data", "width": 160},
		{"label": "Valor", "fieldname": "valor", "fieldtype": "Currency", "width": 140},
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

	if filters.get("cj_tipo"):
		conditions.append("fi.cj_tipo = %(cj_tipo)s")
		values["cj_tipo"] = filters["cj_tipo"]

	if filters.get("data_inicio"):
		conditions.append("fi.cj_data >= %(data_inicio)s")
		values["data_inicio"] = filters["data_inicio"]

	if filters.get("data_fim"):
		conditions.append("fi.cj_data <= %(data_fim)s")
		values["data_fim"] = filters["data_fim"]

	where = " and ".join(conditions) if conditions else "1=1"
	query = f"""
		select
			date_format(fi.cj_data, '%%Y-%%m') as competencia,
			pj.company,
			fi.cj_tipo,
			sum(ifnull(fi.cj_valor, 0)) as valor
		from `tabCJ Item Financeiro` fi
		inner join `tabProcesso Judicial` pj on pj.name = fi.parent
		where {where}
		group by competencia, pj.company, fi.cj_tipo
		order by competencia asc, pj.company asc, fi.cj_tipo asc
	"""

	rows = frappe.db.sql(query, values, as_dict=True)
	for row in rows:
		if row["competencia"]:
			row["competencia"] = formatdate(f"{row['competencia']}-01")
	return rows
