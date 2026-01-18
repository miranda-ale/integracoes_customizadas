import frappe
from frappe.utils import getdate, nowdate

ALERTA_DIAS = [60, 30, 15, 7, 3, 1, 0]

def processar_alertas_contratos():
    hoje = getdate(nowdate())

    contratos = frappe.get_all(
        "Contrato de Trabalho",
        filters={
            "docstatus": 1,  # submittable: só contratos submetidos
            "status": ["not in", ["Encerrado", "Cancelado"]],
            "data_rescisao": ["is", "not set"],
        },
        fields=["name", "colaborador", "empresa", "tipo_contrato", "proximo_vencimento", "dias_para_vencimento"]
    )

    for c in contratos:
        if not c.get("proximo_vencimento"):
            continue

        dias = c.get("dias_para_vencimento")
        if dias is None:
            # recalcular se precisar
            dias = frappe.datetime.get_day_diff(getdate(c.proximo_vencimento), hoje)

        if int(dias) not in ALERTA_DIAS:
            continue

        # Evita spam: grave no Communication/Comment ou num campo 'alerta_enviado_em'
        # Aqui: usa Comment simples por dia + tipo
        key = f"ALERTA_VENCIMENTO_{int(dias)}_{hoje}"
        ja = frappe.db.exists("Comment", {"reference_doctype": "Contrato de Trabalho", "reference_name": c.name, "content": ["like", f"%{key}%"]})
        if ja:
            continue

        # destinatários: adapte (RH do departamento, responsável, etc.)
        # por padrão: System Managers
        destinatarios = [u.name for u in frappe.get_all("User", filters={"enabled": 1}, fields=["name"])]

        assunto = f"[Contrato] Vencimento em {int(dias)} dia(s) — {c.name}"
        msg = (
            f"{key}\n\n"
            f"Contrato: {c.name}\n"
            f"Colaborador: {c.colaborador}\n"
            f"Empresa: {c.empresa}\n"
            f"Tipo: {c.tipo_contrato}\n"
            f"Vencimento: {c.proximo_vencimento}\n"
            f"Dias para vencimento: {int(dias)}\n"
        )

        # Log na timeline do contrato
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Comment",
            "reference_doctype": "Contrato de Trabalho",
            "reference_name": c.name,
            "content": msg
        }).insert(ignore_permissions=True)

        # Envio de e-mail (opcional)
        # Se preferir Notification do Frappe (UI), não precisa disso aqui.
        try:
            frappe.sendmail(
                recipients=destinatarios,
                subject=assunto,
                message=msg.replace("\n", "<br>")
            )
        except Exception:
            # Não quebra o scheduler
            frappe.log_error(frappe.get_traceback(), "Erro ao enviar alerta de vencimento de contrato")

    frappe.db.commit()
