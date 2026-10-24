from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def ensure_notification_field():
	create_custom_fields(
		{
			"Notification": [
				{
					"fieldname": "send_whatsapp",
					"fieldtype": "Check",
					"label": "Enviar também por WhatsApp",
					"description": "Envia o assunto e a mensagem aos celulares dos usuários destinatários.",
					"insert_after": "send_system_notification",
					"default": "0",
				},
				{
					"fieldname": "modelo_whatsapp",
					"fieldtype": "Link",
					"options": "Modelo WhatsApp",
					"label": "Modelo WhatsApp",
					"description": "Texto próprio do WhatsApp, com ao menos 10 variantes ativas (obrigatório com WhatsApp).",
					"insert_after": "send_whatsapp",
					"depends_on": "send_whatsapp",
					"mandatory_depends_on": "send_whatsapp",
				},
				{
					"fieldname": "whatsapp_numeros_extras",
					"fieldtype": "Small Text",
					"label": "Números WhatsApp adicionais",
					"description": "Um número por linha (ex.: 11 99999-1234). Aceita Jinja, ex.: {{ doc.celular }}. Complementa os destinatários da tabela.",
					"insert_after": "modelo_whatsapp",
					"depends_on": "send_whatsapp",
				},
			]
		},
		update=True,
	)
