import re

import frappe

LEGAL_ROLES = {
	"CJ Administrador",
	"CJ Gestor Jurídico",
	"CJ Analista Jurídico",
}

RESTRICTED_ROLES = {
	"Financeiro Contencioso",
	"RH/DP Contencioso",
}

VIEWER_ROLES = {
	"CJ Visualizador",
}


def user_has_any_role(user, roles):
	return any(role in frappe.get_roles(user) for role in roles)


def is_legal_user(user=None):
	user = user or frappe.session.user
	return user_has_any_role(user, LEGAL_ROLES)


def allowed_sigilo_levels(user=None):
	user = user or frappe.session.user
	if user_has_any_role(user, {"CJ Administrador", "CJ Gestor Jurídico"}):
		return ["Publico", "Restrito", "Sigiloso"]
	if user_has_any_role(user, {"CJ Analista Jurídico"}):
		return ["Publico", "Restrito"]
	if user_has_any_role(user, RESTRICTED_ROLES):
		return ["Publico", "Restrito"]
	if user_has_any_role(user, VIEWER_ROLES):
		return ["Publico"]
	return ["Publico"]


def mask_cpf_cnpj(value):
	if not value:
		return value
	digits = re.sub(r"\D", "", value)
	if len(digits) == 11:
		return f"{digits[:3]}.***.***-{digits[-2:]}"
	if len(digits) == 14:
		return f"{digits[:2]}.***.***/****-{digits[-2:]}"
	return value
