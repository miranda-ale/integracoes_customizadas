"""Agenda do Processo Judicial: ToDo/Event de audiências e prazos e alerta de vencimento."""

import frappe
from frappe import _
from frappe.utils import add_days, add_to_date, get_datetime, getdate, today

DIAS_ALERTA_PRAZO = 3


def sincronizar(processo):
	"""Mantém um ToDo (e um Event, nas audiências) por linha, sem duplicar na reexecução."""
	anterior = processo.get_doc_before_save()
	atuais = {linha.name for linha in processo.audiencias}
	for removida in (anterior.audiencias if anterior else []):
		if removida.name not in atuais:
			_encerrar(removida, "Cancelled")

	for linha in processo.audiencias:
		antes = next((a for a in (anterior.audiencias if anterior else []) if a.name == linha.name), None)
		if antes and get_datetime(antes.data_hora) != get_datetime(linha.data_hora):
			linha.alerta_enviado_em = None
			frappe.db.set_value(linha.doctype, linha.name, "alerta_enviado_em", None, update_modified=False)
		if linha.resultado:
			_encerrar(linha, "Closed")
		else:
			_manter(processo, linha)


def _encerrar(linha, status):
	if linha.todo and frappe.db.exists("ToDo", linha.todo):
		frappe.db.set_value("ToDo", linha.todo, "status", status)
	if linha.evento and frappe.db.exists("Event", linha.evento):
		frappe.db.set_value("Event", linha.evento, "status", "Closed" if status == "Closed" else "Cancelled")


def _manter(processo, linha):
	titulo = f"{linha.categoria}: {linha.tipo or processo.numero_processo or processo.name}"
	descricao = _("{0} – processo {1}{2}").format(
		titulo, processo.numero_processo or processo.name, f" ({linha.local})" if linha.local else ""
	)
	usuario = linha.responsavel or processo.responsavel_interno or processo.owner
	inicio = get_datetime(linha.data_hora)

	valores = {
		"allocated_to": usuario,
		"date": inicio.date(),
		"description": descricao,
		"status": "Open",
		"reference_type": "Processo Judicial",
		"reference_name": processo.name,
	}
	linha.todo = _gravar("ToDo", linha, "todo", valores)

	if linha.categoria == "Audiência":
		valores_evento = {
			"subject": titulo,
			"starts_on": inicio,
			"ends_on": add_to_date(inicio, hours=1),
			"event_type": "Private",
			"status": "Open",
			"description": descricao,
		}
		linha.evento = _gravar("Event", linha, "evento", valores_evento, processo=processo)
	elif linha.evento:
		_encerrar(linha, "Cancelled")
		linha.evento = None
		frappe.db.set_value(linha.doctype, linha.name, "evento", None, update_modified=False)


def _gravar(doctype, linha, campo, valores, processo=None):
	nome = linha.get(campo)
	if nome and frappe.db.exists(doctype, nome):
		documento = frappe.get_doc(doctype, nome)
		documento.update(valores)
		documento.flags.ignore_permissions = True
		documento.save()
		return nome
	documento = frappe.get_doc({"doctype": doctype, **valores})
	if processo:
		documento.append(
			"event_participants", {"reference_doctype": "Processo Judicial", "reference_docname": processo.name}
		)
	documento.flags.ignore_permissions = True
	documento.insert()
	frappe.db.set_value(linha.doctype, linha.name, campo, documento.name, update_modified=False)
	return documento.name


def alertar_prazos():
	"""Job diário: avisa o responsável, uma vez, dos prazos abertos vencidos ou que vencem em até DIAS_ALERTA_PRAZO dias."""
	limite = f"{add_days(today(), DIAS_ALERTA_PRAZO)} 23:59:59"
	linhas = frappe.get_all(
		"Processo Judicial Audiencia",
		filters={
			"parenttype": "Processo Judicial",
			"categoria": "Prazo",
			"data_hora": ["<=", limite],
			"alerta_enviado_em": ["is", "not set"],
			"resultado": ["is", "not set"],
		},
		fields=["name", "parent", "tipo", "data_hora", "responsavel"],
	)
	for linha in linhas:
		processo = frappe.db.get_value(
			"Processo Judicial", linha.parent, ["numero_processo", "responsavel_interno", "owner"], as_dict=True
		)
		destino = linha.responsavel or processo.responsavel_interno or processo.owner
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": destino,
				"type": "Alert",
				"document_type": "Processo Judicial",
				"document_name": linha.parent,
				"subject": _("Prazo {0} vence em {1} – processo {2}").format(
					linha.tipo or "", getdate(linha.data_hora).strftime("%d/%m/%Y"), processo.numero_processo or linha.parent
				),
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Processo Judicial Audiencia", linha.name, "alerta_enviado_em", today(), update_modified=False)
