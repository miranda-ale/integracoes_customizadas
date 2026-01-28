import frappe
from frappe.utils import add_days, today

from integracoes_customizadas.contencioso.utils import allowed_sigilo_levels


def _count_prazos_ate(dias):
	ate = add_days(today(), dias)
	sigilo = allowed_sigilo_levels()
	query = """
		select count(pp.name)
		from `tabCJ Prazo` pp
		inner join `tabProcesso Judicial` pj on pj.name = pp.parent
		where pp.cj_data_vencimento between %(hoje)s and %(ate)s
			and pp.cj_status_prazo = 'A Vencer'
			and pj.cj_nivel_sigilo in %(sigilo)s
	"""
	return frappe.db.sql(query, {"hoje": today(), "ate": ate, "sigilo": sigilo})[0][0]


def prazos_proximos_7():
	return _card_value(
		_count_prazos_ate(7),
		"Int",
		["query-report", "Prazos a vencer"],
		{"data_fim": add_days(today(), 7)},
	)


def prazos_proximos_15():
	return _card_value(
		_count_prazos_ate(15),
		"Int",
		["query-report", "Prazos a vencer"],
		{"data_fim": add_days(today(), 15)},
	)


def prazos_proximos_30():
	return _card_value(
		_count_prazos_ate(30),
		"Int",
		["query-report", "Prazos a vencer"],
		{"data_fim": add_days(today(), 30)},
	)


def custos_ytd():
	ano_inicio = f"{today()[:4]}-01-01"
	sigilo = allowed_sigilo_levels()
	query = """
		select sum(ifnull(fi.cj_valor, 0))
		from `tabCJ Item Financeiro` fi
		inner join `tabProcesso Judicial` pj on pj.name = fi.parent
		where fi.cj_data >= %(inicio)s
			and pj.cj_nivel_sigilo in %(sigilo)s
	"""
	total = frappe.db.sql(query, {"inicio": ano_inicio, "sigilo": sigilo})[0][0] or 0
	return _card_value(
		total,
		"Currency",
		["query-report", "Custos do Contencioso por período"],
		{"data_inicio": ano_inicio},
	)


def audiencias_futuras_30():
	ate = add_days(today(), 30)
	sigilo = allowed_sigilo_levels()
	query = """
		select count(aud.name)
		from `tabCJ Audiencia` aud
		inner join `tabProcesso Judicial` pj on pj.name = aud.parent
		where aud.cj_data_hora >= %(hoje)s
			and aud.cj_data_hora <= %(ate)s
			and pj.cj_nivel_sigilo in %(sigilo)s
	"""
	total = frappe.db.sql(query, {"hoje": today(), "ate": ate, "sigilo": sigilo})[0][0]
	return _card_value(
		total,
		"Int",
		["query-report", "Prazos a vencer"],
		{},
	)


def _card_value(value, fieldtype, route, route_options):
	return {
		"value": value,
		"fieldtype": fieldtype,
		"route": route,
		"route_options": route_options,
	}
