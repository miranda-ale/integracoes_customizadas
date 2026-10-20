import base64
import binascii
from io import BytesIO
from urllib.parse import quote

import frappe
import pyqrcode
import requests
from frappe import _

from integracoes_customizadas.whatsapp.distribuidor import nomes as nomes_instancias


class EvolutionHTTPError(ValueError):
	def __init__(self, message, status):
		super().__init__(message)
		self.status = status


def require_manager():
	if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
		frappe.throw(_("Acesso restrito a administradores."), frappe.PermissionError)


def get_settings():
	settings = frappe.get_single("Configuracoes WhatsApp")
	if not settings.server_url or not settings.instance_name:
		frappe.throw(_("Configure a URL e o nome da instância do WhatsApp."))
	if not settings.get_password("api_key", raise_exception=False):
		frappe.throw(_("Configure a chave da Evolution API."))
	if settings.get("ativo") in (0, "0"):  # None = configuração anterior ao campo; tratada como ativa
		frappe.throw(_("O conector WhatsApp está desativado."))
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
		status = exc.response.status_code
		detail = (exc.response.text or "")[:200]
		frappe.log_error(f"Evolution {method} {path}: HTTP {status} {detail}", "Evolution API")
		message = _("Evolution API respondeu com HTTP {0}.").format(status)
		if detail:
			message = f"{message} {detail}"
		raise EvolutionHTTPError(message, status) from exc
	except (requests.RequestException, ValueError) as exc:
		raise ValueError(_("Não foi possível comunicar com a Evolution API.")) from exc


def resolve_instance(instancia=None):
	"""Valida `instancia` contra as configuradas; sem ela, a principal."""
	settings = get_settings()
	if not instancia:
		return settings.instance_name
	if instancia not in nomes_instancias(settings):
		frappe.throw(_("Instância {0} não está configurada.").format(instancia))
	return instancia


def instance_path(endpoint, instancia=None):
	return f"instance/{endpoint}/{quote(resolve_instance(instancia), safe='')}"


def message_path(endpoint, instancia=None):
	return f"message/{endpoint}/{quote(resolve_instance(instancia), safe='')}"


@frappe.whitelist(methods=["POST"])
def create_instance(instancia=None):
	require_manager()
	nome = resolve_instance(instancia)
	try:
		try:
			instances = evolution_request(
				"GET", "instance/fetchInstances", params={"instanceName": nome}
			)
		except EvolutionHTTPError as exc:
			if exc.status != 404:
				raise
			instances = []
		if isinstance(instances, dict):
			instances = instances.get("instances", [instances])
		if any(
			(item.get("name") or item.get("instanceName") or (item.get("instance") or {}).get("instanceName"))
			== nome
			for item in instances if isinstance(item, dict)
		):
			return {"created": False, "instance_name": nome}
		evolution_request(
			"POST",
			"instance/create",
			json={"instanceName": nome, "integration": "WHATSAPP-BAILEYS", "qrcode": True},
		)
		return {"created": True, "instance_name": nome}
	except ValueError as exc:
		frappe.throw(str(exc))


@frappe.whitelist(methods=["GET"])
def get_connection_state():
	"""`state` da instância principal (compatível) e `instancias` com o estado de cada uma."""
	require_manager()
	estados = {}
	for posicao, nome in enumerate(nomes_instancias(get_settings())):
		try:
			data = evolution_request("GET", instance_path("connectionState", nome))
			estados[nome] = (data.get("instance") or {}).get("state") or "desconhecido"
		except ValueError as exc:
			if posicao == 0:  # a principal indisponível é erro; as adicionais só aparecem como indisponíveis
				frappe.throw(str(exc))
			estados[nome] = "indisponivel"
	return {"state": next(iter(estados.values())), "instancias": estados}


@frappe.whitelist(methods=["POST"])
def get_qr_code(instancia=None):
	require_manager()
	try:
		data = evolution_request("GET", instance_path("connect", instancia))
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
