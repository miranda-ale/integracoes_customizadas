"""Corpo de e-mail no layout institucional da BHCL (manifesto do clm, seção 6).

O layout mora no `clm` (`render_email`), que não é dependência deste app: sem ele instalado, o mesmo conteúdo segue em HTML simples.
"""

import frappe
from frappe.utils import escape_html


def _render_email():
	if "clm" not in frappe.get_installed_apps():
		return None
	try:
		from clm.clm.services.email_layout import render_email
	except ImportError:
		return None
	return render_email


def ja_institucional(html) -> bool:
	try:
		from clm.clm.services.email_layout import is_branded
	except ImportError:
		return False
	return is_branded(html)


def corpo(titulo, corpo_html, fatos=None, acao=None, nota=None) -> str:
	"""`titulo` é texto puro (é escapado); `corpo_html` é HTML confiável (dados de usuário já escapados);
	`fatos` [(rótulo, valor)] são escapados pelo layout."""
	if ja_institucional(corpo_html):
		return corpo_html
	render_email = _render_email()
	if not render_email:
		return _sem_layout(corpo_html, fatos, acao, nota)
	return render_email(escape_html(titulo or ""), corpo_html, facts=fatos, action=acao, note=nota)


def _sem_layout(corpo_html, fatos, acao, nota) -> str:
	"""Sem o clm: o mesmo conteúdo em HTML simples (nenhum fato, botão ou nota se perde)."""
	partes = [corpo_html or ""]
	partes += [f"<p><b>{escape_html(str(r))}:</b> {escape_html(str(v or '—'))}</p>" for r, v in fatos or []]
	if acao:
		partes.append(f'<p><a href="{acao[1]}">{escape_html(str(acao[0]))}</a></p>')
	if nota:
		partes.append(f"<p><small>{escape_html(str(nota))}</small></p>")
	return "".join(partes)
