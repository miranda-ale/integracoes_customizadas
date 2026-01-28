import frappe
from frappe.utils import now_datetime


def executar_sync_stub():
	"""Stub de integração (desativado por padrão)."""
	if not frappe.conf.get("contencioso_integracao_ativa"):
		return

	frappe.logger("contencioso").info("Stub de integração executado em %s", now_datetime())
