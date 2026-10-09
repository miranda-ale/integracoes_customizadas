import re

import frappe
from frappe.utils import now_datetime

from integracoes_customizadas.whatsapp.api import evolution_request, instance_path, message_path


def normalize_phone(value):
	value = (value or "").strip()
	if not value:
		return None
	if not re.fullmatch(r"\+?[\d\s().-]+", value):
		return None
	digits = re.sub(r"\D", "", value)
	if value.startswith("+"):
		return digits if 8 <= len(digits) <= 15 else None
	if len(digits) in {10, 11}:
		return "55" + digits
	if digits.startswith("55") and len(digits) in {12, 13}:
		return digits
	return None


def send_delivery(delivery_name):
	delivery = frappe.get_doc("Envio WhatsApp", delivery_name, for_update=True)
	if delivery.status != "Pendente":
		return
	delivery.db_set("attempts", (delivery.attempts or 0) + 1)
	try:
		state = evolution_request("GET", instance_path("connectionState"))
		if (state.get("instance") or {}).get("state") != "open":
			raise ValueError("Instância WhatsApp desconectada.")
		response = evolution_request(
			"POST", message_path("sendText"),
			json={"number": delivery.phone, "text": delivery.message},
		)
		delivery.db_set(
			{
				"status": "Enviado",
				"provider_message_id": (response.get("key") or {}).get("id"),
				"sent_at": now_datetime(),
				"error": None,
			}
		)
	except Exception as exc:
		if isinstance(exc, (ValueError, frappe.ValidationError)):
			reason = str(exc)
		else:
			reason = "Erro interno ao enviar pelo WhatsApp. Consulte o Error Log."
			frappe.log_error(frappe.get_traceback(), "Falha no envio WhatsApp")
		delivery.db_set({"status": "Falhou", "error": reason[:140]})
