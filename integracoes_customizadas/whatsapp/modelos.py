"""Modelos dedicados de WhatsApp: texto próprio (sem reaproveitar o corpo HTML de e-mail) com Jinja.

Cada valor interpolado é limpo de HTML, `None` vira vazio e `*`/`_`/`~` do dado não quebram a formatação.
"""

import re

import frappe
from bs4 import BeautifulSoup
from frappe import _
from frappe.utils import cstr, format_datetime, formatdate, get_datetime
from jinja2.sandbox import SandboxedEnvironment

from integracoes_customizadas.whatsapp import conector

MODELO = "Modelo WhatsApp"
_MARCADORES = re.compile(r"([*_~])(?=\S)")


def _proteger(valor) -> str:
	"""Dado variável: sem HTML e sem marcadores soltos (U+200B entre o marcador e o texto)."""
	texto = cstr(valor)
	if "<" in texto:
		texto = BeautifulSoup(texto, "html.parser").get_text("\n", strip=True)
	return _MARCADORES.sub("\\1\u200b", texto)


# Sandbox próprio: `None` vira vazio (o Jinja do Frappe imprimiria "None") e nada é escapado como HTML.
_ENV = SandboxedEnvironment(finalize=lambda v: "" if v is None else v, autoescape=False)


def contexto(doc, extra=None) -> dict:
	return {
		"doc": doc,
		"extra": frappe._dict(extra or {}),
		"data": lambda v, fmt=None: formatdate(v, fmt) if v else "",
		"data_hora": lambda v: format_datetime(v) if v else "",
		"hora": lambda v: get_datetime(v).strftime("%H:%M") if v else "",
		"seguro": _proteger,
		"url": frappe.utils.get_url,
	}


def _renderizar_texto(template, ctx) -> str:
	texto = _ENV.from_string(template or "").render(**ctx).replace("\r\n", "\n")
	texto = re.sub(r"[ \t]+\n", "\n", texto)
	return re.sub(r"\n{3,}", "\n\n", texto).strip()


def obter_modelo(nome):
	modelo = frappe.get_cached_doc(MODELO, nome)
	if not modelo.ativo:
		frappe.throw(_("O Modelo WhatsApp {0} está inativo.").format(nome))
	return modelo


def renderizar(modelo, doc, extra=None) -> dict:
	"""→ {"texto": WhatsApp, "assunto": str, "html": corpo do e-mail}."""
	if isinstance(modelo, str):
		modelo = obter_modelo(modelo)
	ctx = contexto(doc, extra)
	texto = _renderizar_texto(modelo.mensagem, ctx)
	assunto = _renderizar_texto(modelo.assunto_email, ctx) if modelo.assunto_email else modelo.titulo
	if modelo.mensagem_email:
		html = _ENV.from_string(modelo.mensagem_email).render(**ctx)
	else:
		html = _para_html(texto)
	return {"texto": texto, "assunto": assunto, "html": html}


def _para_html(texto) -> str:
	try:
		from assinatura_eletronica.servicos.canais import whatsapp_para_html
	except ImportError:
		return frappe.utils.escape_html(texto).replace("\n", "<br>")
	return whatsapp_para_html(texto)


def registrar_envio(*, telefone, mensagem, doc=None, status, erro=None, message_id=None, modelo=None):
	frappe.get_doc(
		{
			"doctype": "Envio WhatsApp",
			"status": status,
			"phone": telefone,
			"reference_doctype": doc.doctype if doc else None,
			"reference_name": doc.name if doc else None,
			"message": mensagem,
			"attempts": 1,
			"provider_message_id": message_id,
			"error": (erro or "")[:140] or None,
		}
	).insert(ignore_permissions=True)


def enviar_whatsapp(telefone, texto, doc=None) -> tuple[bool, str | None]:
	"""Envia pelo conector estrito. → (ok, motivo da falha)."""
	numero = conector.normalizar_numero_br(telefone)
	if not numero:
		registrar_envio(telefone=None, mensagem=texto, doc=doc, status="Ignorado", erro="Celular inválido.")
		return False, _("Celular inválido.")
	try:
		resposta = conector.enviar_texto(numero, texto)
	except (conector.NumeroInvalido, conector.EvolutionIndisponivel, conector.EnvioRejeitado) as exc:
		registrar_envio(telefone=numero, mensagem=texto, doc=doc, status="Falhou", erro=str(exc))
		return False, str(exc)
	registrar_envio(
		telefone=numero, mensagem=texto, doc=doc, status="Enviado", message_id=resposta.get("message_id")
	)
	return True, None


def enviar_email(email, assunto, html):
	frappe.sendmail(recipients=[email], subject=assunto, message=html, now=False)


def enviar_modelo(modelo, doc, *, telefone=None, email=None, canal="WhatsApp", extra=None) -> dict:
	"""Envia o modelo pelo canal pedido ('WhatsApp', 'E-mail' ou 'Ambos').

	WhatsApp sem telefone válido ou com falha cai para e-mail (se houver). → {"canais": [...], "erro": str|None}.
	"""
	conteudo = renderizar(modelo, doc, extra)
	enviados, erros = [], []
	if canal in ("WhatsApp", "Ambos") and telefone:
		ok, erro = enviar_whatsapp(telefone, conteudo["texto"], doc)
		(enviados if ok else erros).append("WhatsApp" if ok else erro)
	elif canal in ("WhatsApp", "Ambos"):
		erros.append(_("Sem telefone cadastrado."))
	usar_email = canal in ("E-mail", "Ambos") or (canal == "WhatsApp" and "WhatsApp" not in enviados)
	if usar_email and email:
		enviar_email(email, conteudo["assunto"], conteudo["html"])
		enviados.append("E-mail")
	elif usar_email and canal != "WhatsApp":
		erros.append(_("Sem e-mail cadastrado."))
	return {"canais": enviados, "erro": None if enviados else "; ".join(erros) or _("Nenhum canal disponível.")}
