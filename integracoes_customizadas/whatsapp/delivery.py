import re

import frappe
from frappe.utils import now_datetime

from integracoes_customizadas.whatsapp.api import evolution_request, instance_path, message_path
from integracoes_customizadas.whatsapp.conector import corpo_documento, normalizar_numero_br
from integracoes_customizadas.whatsapp.distribuidor import SemInstanciaDisponivel, escolher_instancia


def normalize_phone(value):
	"""Mesmo critério do conector (DDD e nono dígito validados); números internacionais (+) passam como estão."""
	value = (value or "").strip()
	if value.startswith("+") and re.fullmatch(r"\+[\d\s().-]+", value):
		digits = re.sub(r"\D", "", value)
		return digits if 8 <= len(digits) <= 15 else None
	return normalizar_numero_br(value)


TAMANHO_MAXIMO_ANEXO = 15 * 1024 * 1024
TIMEOUT_MIDIA = (5, 60)  # PDF em base64 demora mais que texto


def nome_anexo(reference_name):
	return re.sub(r"[^A-Za-z0-9._-]+", "-", str(reference_name)).strip("-") + ".pdf"


def gerar_anexo(delivery):
	"""PDF do Print Format no momento do envio (como o e-mail da Notification); nada é guardado no banco."""
	doc = frappe.get_doc(delivery.reference_doctype, delivery.reference_name)
	print_settings = frappe.get_cached_doc("Print Settings")
	if doc.get("docstatus") == 0 and not print_settings.allow_print_for_draft:
		raise ValueError("Documento em rascunho não pode ser impresso.")
	if doc.get("docstatus") == 2 and not print_settings.allow_print_for_cancelled:
		raise ValueError("Documento cancelado não pode ser impresso.")
	anexo = frappe.attach_print(
		doc.doctype,
		doc.name,
		file_name=(delivery.nome_arquivo or nome_anexo(doc.name)).removesuffix(".pdf"),
		print_format=delivery.print_format,
		lang=doc.get("language") or frappe.db.get_value("Print Format", delivery.print_format, "default_print_language"),
	)
	conteudo = anexo["fcontent"]
	if not conteudo.startswith(b"%PDF"):
		raise ValueError("O formato de impressão não gerou PDF (verifique Print Settings).")
	if len(conteudo) > TAMANHO_MAXIMO_ANEXO:
		raise ValueError("PDF acima do limite de 15 MB para envio pelo WhatsApp.")
	return conteudo


def send_delivery(delivery_name):
	delivery = frappe.get_doc("Envio WhatsApp", delivery_name, for_update=True)
	if delivery.status != "Pendente":
		return
	delivery.db_set("attempts", (delivery.attempts or 0) + 1)
	try:
		try:
			instancia = escolher_instancia(delivery.phone, preferida=getattr(delivery, "instancia", None))
		except SemInstanciaDisponivel as exc:
			raise ValueError("Nenhuma instância WhatsApp conectada.") from exc
		delivery.db_set("instancia", instancia)
		state = evolution_request("GET", instance_path("connectionState", instancia))
		if (state.get("instance") or {}).get("state") != "open":
			raise ValueError("Instância WhatsApp desconectada.")
		if delivery.get("print_format"):
			corpo = corpo_documento(gerar_anexo(delivery), delivery.nome_arquivo, delivery.message)
			response = evolution_request(
				"POST", message_path("sendMedia", instancia),
				json={"number": delivery.phone, **corpo},
				timeout=TIMEOUT_MIDIA,
			)
		else:
			response = evolution_request(
				"POST", message_path("sendText", instancia),
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
