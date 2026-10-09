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
				}
			]
		},
		update=True,
	)
