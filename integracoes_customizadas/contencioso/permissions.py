import frappe

from integracoes_customizadas.contencioso.utils import allowed_sigilo_levels


def processo_judicial_query_conditions(user):
	niveis = allowed_sigilo_levels(user)
	placeholders = ", ".join([f"'{n}'" for n in niveis])
	return f"`tabProcesso Judicial`.cj_nivel_sigilo in ({placeholders})"


def processo_judicial_has_permission(doc, user=None):
	user = user or frappe.session.user
	return doc.cj_nivel_sigilo in allowed_sigilo_levels(user)
