"""Ponto de extensão para webhooks de status da Evolution API (preparado, NÃO implementado).

Outros apps registram handlers no hook `evolution_webhook_handlers` (caminhos pontilhados). Cada handler
recebe um evento já normalizado:

	{"message_id": str, "status": "enviado"|"entregue"|"lido"|"falhou", "ocorrido_em": datetime, "bruto": dict}
"""

import frappe

STATUS_VALIDOS = ("enviado", "entregue", "lido", "falhou")


def despachar_evento(evento: dict) -> int:
	"""Chama cada handler registrado; falha de um não impede os demais. Devolve quantos rodaram sem erro."""
	if (
		not isinstance(evento, dict)
		or evento.get("status") not in STATUS_VALIDOS
		or not evento.get("message_id")
	):
		raise ValueError("Evento de webhook fora do contrato normalizado.")
	executados = 0
	for caminho in frappe.get_hooks("evolution_webhook_handlers"):
		try:
			frappe.get_attr(caminho)(evento)
			executados += 1
		except Exception:
			frappe.log_error(title=f"Webhook Evolution: handler {caminho} falhou")
	return executados


@frappe.whitelist(allow_guest=True, methods=["POST"])
def webhook_evolution():
	"""Recebe eventos da Evolution API. Desligado: responde 501 sem processar nada.

	TODO(webhooks):
	- autenticar por chave/HMAC (`webhook_segredo`) com `hmac.compare_digest`;
	- mapear os eventos da v2 [VERIFICAR] (ex.: MESSAGES_UPDATE, SEND_MESSAGE, CONNECTION_UPDATE) para o
	  evento normalizado e chamar `despachar_evento`;
	- idempotência por (message_id, status);
	- responder rápido e processar em fila (`frappe.enqueue`).
	"""
	if not frappe.db.get_single_value("Configuracoes WhatsApp", "webhook_habilitado"):
		frappe.local.response["http_status_code"] = 501
		return {"erro": "Webhook desabilitado."}
	frappe.local.response["http_status_code"] = 501
	return {"erro": "Webhook ainda não implementado."}
