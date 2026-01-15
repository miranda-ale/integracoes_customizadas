import frappe
from xml.etree.ElementTree import Element, SubElement, tostring
from frappe.utils import getdate

def _fmt_date_ddmmyyyy(d):
    if not d:
        return ""
    dt = getdate(d)
    return dt.strftime("%d/%m/%Y")

def _get_bionexo_codigo_produto(item_doc):
    """
    Ajuste conforme sua estratégia:
    - Campo custom no Item: custom_bionexo_codigo_produto
    - Ou outra fonte (tabela de conversão, etc.)
    """
    # Exemplo com custom field no Item
    code = frappe.db.get_value("Item", item_doc.item_code, "custom_bionexo_codigo_produto")
    if not code:
        frappe.throw(
            f"Item {item_doc.item_code} sem 'custom_bionexo_codigo_produto' preenchido. "
            "Necessário para exportação Bionexo."
        )
    return str(code)

def _get_header_value(doc, fieldname, default=None):
    # Lê campo custom do Material Request se existir
    if hasattr(doc, fieldname):
        val = getattr(doc, fieldname)
        if val not in (None, ""):
            return val
    return default

@frappe.whitelist()
def export_material_request_bionexo_xml(material_request: str):
    doc = frappe.get_doc("Material Request", material_request)

    # Valida docstatus (opcional, mas recomendado)
    if doc.docstatus != 1:
        frappe.throw("Somente é permitido exportar Material Request submetido (docstatus=1).")

    # --- Cabeçalho: você pode parametrizar via campos custom no MR ---
    requisicao = _get_header_value(doc, "custom_bionexo_requisicao", doc.name)
    moeda = _get_header_value(doc, "custom_bionexo_moeda", "Reais")
    observacao = _get_header_value(doc, "custom_bionexo_observacao", (doc.title or ""))
    tipo_cotacao = _get_header_value(doc, "custom_bionexo_tipo_cotacao", "100")
    titulo_pdc = _get_header_value(doc, "custom_bionexo_titulo_pdc", (doc.title or doc.name))
    id_forma_pagamento = _get_header_value(doc, "custom_bionexo_id_forma_pagamento", "1")

    # Data/hora de vencimento (normalmente a janela de cotação)
    data_vencimento = _fmt_date_ddmmyyyy(_get_header_value(doc, "custom_bionexo_data_vencimento", doc.schedule_date))
    hora_vencimento = _get_header_value(doc, "custom_bionexo_hora_vencimento", "00:00")

    # --- Monta XML no exato padrão do Bionexo ---
    root = Element("xml")
    pedido = SubElement(root, "Pedido")

    cab = SubElement(pedido, "Cabecalho")
    SubElement(cab, "Requisicao").text = str(requisicao)
    SubElement(cab, "Moeda").text = str(moeda)
    SubElement(cab, "Observacao").text = str(observacao)
    SubElement(cab, "Tipo_Cotacao").text = str(tipo_cotacao)
    SubElement(cab, "Titulo_Pdc").text = str(titulo_pdc)
    SubElement(cab, "Id_Forma_Pagamento").text = str(id_forma_pagamento)
    SubElement(cab, "Data_Vencimento").text = str(data_vencimento)
    SubElement(cab, "Hora_Vencimento").text = str(hora_vencimento)

    itens_req = SubElement(pedido, "Itens_Requisicao")

    for it in doc.items:
        item_el = SubElement(itens_req, "Item_Requisicao")

        codigo_prod = _get_bionexo_codigo_produto(it)
        SubElement(item_el, "Codigo_Produto").text = codigo_prod
        SubElement(item_el, "Quantidade").text = str(it.qty or 0)

        # Programacao_Entrega (opcional)
        # Caso você crie uma child table custom com entregas parciais, implemente aqui.
        # Exemplo: se existisse it.custom_entregas (lista) com campos data/quantidade.
        # for pe in (getattr(it, "custom_programacoes_entrega", []) or []):
        #     pe_el = SubElement(item_el, "Programacao_Entrega")
        #     SubElement(pe_el, "Data").text = _fmt_date_ddmmyyyy(pe.data)
        #     SubElement(pe_el, "Quantidade").text = str(pe.quantidade)

    xml_bytes = tostring(root, encoding="utf-8", method="xml")
    filename = f"BIONEXO_{doc.name}.xml"

    frappe.response["filename"] = filename
    frappe.response["filecontent"] = xml_bytes
    frappe.response["type"] = "download"
