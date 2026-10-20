import json
import re

import frappe
from bs4 import BeautifulSoup
from frappe.core.doctype.role.role import get_users
from frappe.email.doctype.notification.notification import Notification, get_assignees
from frappe.utils import cstr

from integracoes_customizadas.whatsapp.delivery import normalize_phone


class WhatsAppNotification(Notification):
	def send_notification_by_channel(self, doc, context):
		super().send_notification_by_channel(doc, context)
		if not self.get("send_whatsapp"):
			return
		try:
			queue_whatsapp(self, doc, context)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Falha ao preparar notificação WhatsApp")


def _field_values(field_spec, doc):
	"""Valores de `campo` ou `campo,tabela_filha` (mesmo formato do Select de destinatários da Notification)."""
	parts = field_spec.split(",", 1)
	if len(parts) == 2:
		return [child.get(parts[0]) for child in (doc.get(parts[1]) or [])]
	return [doc.get(parts[0])]


def recipient_users(alert, doc, context):
	users = set()
	for row in alert.recipients:
		if row.condition and not frappe.safe_eval(row.condition, None, context):
			continue
		if row.receiver_by_role:
			users.update(["Administrator"] if row.receiver_by_role == "Administrator" else get_users(row.receiver_by_role))
		field_spec = row.receiver_by_document_field
		if field_spec == "owner":
			users.add(doc.owner)
		elif field_spec:
			users.update(value for value in _field_values(field_spec, doc) if value and frappe.db.exists("User", value))
	if alert.send_to_all_assignees:
		users.update(get_assignees(doc))
	return sorted(user for user in users if user and user != "Guest")


def recipient_phones(alert, doc, context):
	"""Telefones brutos sem User: campos do documento que não são User + números extras da regra."""
	phones = []
	for row in alert.recipients:
		field_spec = row.receiver_by_document_field
		if not field_spec or field_spec == "owner":
			continue
		if row.condition and not frappe.safe_eval(row.condition, None, context):
			continue
		phones.extend(
			cstr(value).strip()
			for value in _field_values(field_spec, doc)
			if value and not frappe.db.exists("User", value)
		)
	extras = alert.get("whatsapp_numeros_extras")
	if extras:
		try:
			rendered = frappe.render_template(extras, context)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Falha nos números extras da notificação WhatsApp")
		else:
			phones.extend(item.strip() for item in re.split(r"[\n,;]+", rendered) if item.strip())
	return phones


def render_message(alert, context, destino=None, info=None):
	"""Texto do WhatsApp. Com modelo, sorteia uma variante por `destino`; o id sorteado vai em `info["variante"]`."""
	if alert.get("modelo_whatsapp"):
		from integracoes_customizadas.whatsapp.modelos import renderizar

		conteudo = renderizar(alert.modelo_whatsapp, context["doc"], {"alert": alert}, destino=destino)
		if info is not None:
			info["variante"] = conteudo["variante"]
		return conteudo["texto"]
	subject_template = alert.subject or alert.notification_title or ""
	body_template = alert.message or ""
	if body_template.strip() == "Add your message here":
		body_template = alert.notification_message or ""
	subject = frappe.render_template(subject_template, context) if subject_template else ""
	body = frappe.render_template(body_template, context) if body_template else ""
	subject = BeautifulSoup(subject, "html.parser").get_text(" ", strip=True)
	body = BeautifulSoup(body, "html.parser").get_text("\n", strip=True)
	text = "\n\n".join(part for part in [subject, body] if part)
	return re.sub(r"\n{3,}", "\n\n", text).strip()


def queue_whatsapp(alert, doc, context=None):
	if context is None:
		context = {"doc": doc, "alert": alert, "comments": None}
		if doc.get("_comments"):
			context["comments"] = json.loads(doc.get("_comments"))
	if not render_message(alert, context):
		frappe.log_error(f"Regra {alert.name} sem mensagem para WhatsApp", "Notificação WhatsApp vazia")
		return
	seen = set()
	for user in recipient_users(alert, doc, context):
		info = frappe.db.get_value("User", user, ["enabled", "mobile_no"], as_dict=True)
		if not info or not info.enabled:
			continue
		_register_delivery(alert, doc, context, normalize_phone(cstr(info.mobile_no)), seen, user=user)
	for raw in recipient_phones(alert, doc, context):
		_register_delivery(alert, doc, context, normalize_phone(raw), seen)


def _register_delivery(alert, doc, context, phone, seen, user=None):
	if phone in seen:
		return
	if phone:
		seen.add(phone)
	# Uma redação por destinatário; o roteador não repete a última que esse número recebeu.
	detalhe = {}
	message = render_message(alert, context, destino=phone, info=detalhe)
	delivery = frappe.get_doc(
		{
			"doctype": "Envio WhatsApp",
			"status": "Pendente" if phone else "Ignorado",
			"notification": alert.name,
			"user": user,
			"phone": phone or None,
			"reference_doctype": doc.parenttype if doc.meta.istable else doc.doctype,
			"reference_name": doc.parent if doc.meta.istable else doc.name,
			"message": message,
			"variante": detalhe.get("variante"),
			"error": None if phone else (
				"Celular ausente ou inválido no cadastro do usuário." if user else "Número ausente ou inválido."
			),
		}
	).insert(ignore_permissions=True)
	if phone:
		frappe.enqueue(
			"integracoes_customizadas.whatsapp.delivery.send_delivery",
			queue="short",
			enqueue_after_commit=True,
			delivery_name=delivery.name,
		)
