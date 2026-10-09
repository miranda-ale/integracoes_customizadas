import base64
import binascii
from io import BytesIO
from urllib.parse import quote

import frappe
import pyqrcode
import requests
from frappe import _


def require_manager():
	if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
		frappe.throw(_("Acesso restrito a administradores."), frappe.PermissionError)


def get_settings():
	settings = frappe.get_single("Configuracoes WhatsApp")
	if not settings.server_url or not settings.instance_name:
		frappe.throw(_("Configure a URL e o nome da instância do WhatsApp."))
	if not settings.get_password("api_key", raise_exception=False):
		frappe.throw(_("Configure a chave da Evolution API."))
	return settings


def evolution_request(method, path, *, json=None, params=None):
	settings = get_settings()
	url = f"{settings.server_url.rstrip('/')}/{path.lstrip('/')}"
	try:
		response = requests.request(
			method,
			url,
			headers={"apikey": settings.get_password("api_key"), "Content-Type": "application/json"},
			json=json,
			params=params,
			timeout=(5, 20),
		)
		response.raise_for_status()
		return response.json()
	except requests.HTTPError as exc:
		raise ValueError(_("Evolution API respondeu com HTTP {0}.").format(exc.response.status_code)) from exc
	except (requests.RequestException, ValueError) as exc:
		raise ValueError(_("Não foi possível comunicar com a Evolution API.")) from exc


def instance_path(endpoint):
	return f"instance/{endpoint}/{quote(get_settings().instance_name, safe='')}"


def message_path(endpoint):
	return f"message/{endpoint}/{quote(get_settings().instance_name, safe='')}"


@frappe.whitelist(methods=["POST"])
def create_instance():
	require_manager()
	settings = get_settings()
	try:
		instances = evolution_request(
			"GET", "instance/fetchInstances", params={"instanceName": settings.instance_name}
		)
		if isinstance(instances, dict):
			instances = instances.get("instances", [instances])
		if any(
			(item.get("name") or item.get("instanceName") or (item.get("instance") or {}).get("instanceName"))
			== settings.instance_name
			for item in instances if isinstance(item, dict)
		):
			return {"created": False, "instance_name": settings.instance_name}
		evolution_request(
			"POST",
			"instance/create",
			json={"instanceName": settings.instance_name, "integration": "WHATSAPP-BAILEYS", "qrcode": True},
		)
		return {"created": True, "instance_name": settings.instance_name}
	except ValueError as exc:
		frappe.throw(str(exc))


@frappe.whitelist(methods=["GET"])
def get_connection_state():
	require_manager()
	try:
		data = evolution_request("GET", instance_path("connectionState"))
		return {"state": (data.get("instance") or {}).get("state") or "desconhecido"}
	except ValueError as exc:
		frappe.throw(str(exc))


@frappe.whitelist(methods=["POST"])
def get_qr_code():
	require_manager()
	try:
		data = evolution_request("GET", instance_path("connect"))
		if (data.get("instance") or {}).get("state") == "open":
			return {"state": "open"}
		qr = data.get("qrcode") or data
		if isinstance(qr, dict):
			encoded = qr.get("base64") or ""
			code = qr.get("code")
		else:
			encoded, code = "", None
		if encoded:
			payload = encoded.split(",", 1)[-1]
			try:
				if base64.b64decode(payload, validate=True).startswith(b"\x89PNG\r\n\x1a\n"):
					return {"state": "connecting", "image": f"data:image/png;base64,{payload}"}
			except binascii.Error:
				pass
		if code:
			buffer = BytesIO()
			pyqrcode.create(code).svg(buffer, scale=5)
			return {
				"state": "connecting",
				"image": "data:image/svg+xml;base64," + base64.b64encode(buffer.getvalue()).decode(),
			}
		return {"state": "connecting", "image": None}
	except ValueError as exc:
		frappe.throw(str(exc))


@frappe.whitelist(methods=["POST"])
def retry_delivery(delivery_name):
	require_manager()
	delivery = frappe.get_doc("Envio WhatsApp", delivery_name, for_update=True)
	if delivery.status != "Falhou":
		frappe.throw(_("Somente envios com falha podem ser reenviados."))
	delivery.db_set({"status": "Pendente", "error": None})
	frappe.enqueue(
		"integracoes_customizadas.whatsapp.delivery.send_delivery",
		queue="short",
		enqueue_after_commit=True,
		delivery_name=delivery.name,
	)
	return {"status": "Pendente"}
