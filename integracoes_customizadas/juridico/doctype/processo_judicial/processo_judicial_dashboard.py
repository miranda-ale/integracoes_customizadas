from frappe import _


def get_data():
	return {
		"fieldname": "processo_relacionado",
		"transactions": [
			{"label": _("Jurídico"), "items": ["Processo Judicial"]},
		],
	}
