import frappe
from xml.etree.ElementTree import Element, SubElement, tostring
from frappe.utils import getdate, add_days, nowdate

# Constantes conforme regra definida
TIPO_COTACAO_FIXO = "100"
ID_FORMA_PAGAMENTO_FIXO = "1"   # conforme sua última orientação
MOEDA_FIXA = "Reais"
HORA_VENCIMENTO_FIXA = "14:00"

def _fmt_date_ddmmyyyy(d) -> str:
    if not d:
        return ""
    dt = getdate(d)
    return dt.strftime("%d/%m/%Y")

@frappe.whitelist()
def export_material_request_bionexo_xml(material_request: str):
    """
    Exporta Material Request para XML no formato Bionexo, conforme regras:
    - Cabecalho/Data_Vencimento: 2 dias após a geração do arquivo (today + 2)
    - Cabecalho/Hora_Vencimento: 14:00 fixo
    - Item_Requisicao/Codigo_Produto: item_code (coincidente entre sistemas)
    - Item_Requisicao/Quantidade: qty
    - Programacao_Entrega: sempre 1 quando schedule_date preenchido:
        Data = schedule_date, Quantidade = qty
    - Tipo_Cotacao: 100 fixo
    - Id_Forma_Pagamento: 1 fixo
    """

    doc = frappe.get_doc("Material Request", material_request)

    # Se quiser permitir export mesmo em rascunho, remova esta validação.
    # Recomendo manter para garantir dados consistentes.
    if doc.docstatus != 1:
        frappe.throw("Somente é permitido exportar Material Request submetido (docstatus=1).")

    if not doc.items:
        frappe.throw("Material Request sem itens. Nada a exportar.")

    # --- Cabeçalho ---
    requisicao = doc.name  # alfanumérico permitido
    observacao = (doc.title or "").strip() or "EXPORTADO DO ERPNext"
    titulo_pdc = (doc.title or doc.name).strip()

    # Vencimento: 2 dias após geração do arquivo
    data_vencimento = _fmt_date_ddmmyyyy(add_days(nowdate(), 2))
    hora_vencimento = HORA_VENCIMENTO_FIXA

    # --- XML ---
    root = Element("xml")
    pedido = SubElement(root, "Pedido")

    cab = SubElement(pedido, "Cabecalho")
    SubElement(cab, "Requisicao").text = str(requisicao)
    SubElement(cab, "Moeda").text = MOEDA_FIXA
    SubElement(cab, "Observacao").text = str(observacao)
    SubElement(cab, "Tipo_Cotacao").text = TIPO_COTACAO_FIXO
    SubElement(cab, "Titulo_Pdc").text = str(titulo_pdc)
    SubElement(cab, "Id_Forma_Pagamento").text = ID_FORMA_PAGAMENTO_FIXO
    SubElement(cab, "Data_Vencimento").text = str(data_vencimento)
    SubElement(cab, "Hora_Vencimento").text = str(hora_vencimento)

    itens_req = SubElement(pedido, "Itens_Requisicao")

    for it in doc.items:
        if not it.item_code:
            frappe.throw(f"Item (linha {it.idx}) sem item_code. Não é possível exportar Bionexo.")

        if not it.qty or float(it.qty) <= 0:
            frappe.throw(f"Item {it.item_code} (linha {it.idx}) com qty inválida ({it.qty}).")

        item_el = SubElement(itens_req, "Item_Requisicao")
        SubElement(item_el, "Codigo_Produto").text = str(it.item_code)
        SubElement(item_el, "Quantidade").text = str(it.qty)

        # Programacao_Entrega: sempre uma única quando schedule_date estiver preenchido
        if it.schedule_date:
            pe_el = SubElement(item_el, "Programacao_Entrega")
            SubElement(pe_el, "Data").text = _fmt_date_ddmmyyyy(it.schedule_date)
            SubElement(pe_el, "Quantidade").text = str(it.qty)

    xml_bytes = tostring(root, encoding="utf-8", method="xml")
    filename = f"BIONEXO_{doc.name}.xml"

    frappe.response["filename"] = filename
    frappe.response["filecontent"] = xml_bytes
    frappe.response["type"] = "download"
