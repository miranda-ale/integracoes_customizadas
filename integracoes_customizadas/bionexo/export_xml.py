import re
import frappe
from xml.etree.ElementTree import Element, SubElement, tostring
from frappe.utils import getdate, add_days, nowdate, strip_html, now_datetime

# Regras fixas do layout WA
LAYOUT = "WA"
TIPO_COTACAO_FIXO = "100"
ID_FORMA_PAGAMENTO_FIXO = "641"
MOEDA_FIXA = "Reais"
COD_ESTOQUE_FIXO = "012"
HORA_VENCIMENTO_FIXA = "14:00"

# Limites conforme documentação
MAX_VARCHAR_4000 = 4000

def _make_requisicao_10_digits() -> str:
    # YYMMDDHHMM => 10 dígitos, somente números
    return now_datetime().strftime("%y%m%d%H%M")

def _fmt_date_ddmmyyyy(d) -> str:
    if not d:
        return ""
    dt = getdate(d)
    return dt.strftime("%d/%m/%Y")

def _to_int_string(qty) -> str:
    """
    Bionexo tende a ser sensível a '1200.0'. Força inteiro.
    - Se qty for 1200.0 -> "1200"
    - Se qty for "1200" -> "1200"
    """
    try:
        f = float(qty or 0)
    except Exception:
        f = 0.0
    return str(int(round(f)))

def _sanitize_varchar_4000(text: str) -> str:
    """
    Sanitiza para VARCHAR2(4000):
    - Remove HTML
    - Preserva quebras de linha (transformando alguns fechamentos comuns em '\n')
    - Normaliza espaços e linhas em branco
    - Garante separadores entre sentenças quando vier "colado"
    - Trunca em 4000
    """
    if not text:
        return ""

    # 1) Pré-tratamento para preservar quebras em HTML comum
    # (antes de strip_html, porque strip_html pode "colar" parágrafos)
    html = text
    html = re.sub(r"(?i)</\s*p\s*>", "\n", html)
    html = re.sub(r"(?i)</\s*br\s*>", "\n", html)
    html = re.sub(r"(?i)<\s*br\s*/\s*>", "\n", html)
    html = re.sub(r"(?i)</\s*div\s*>", "\n", html)
    html = re.sub(r"(?i)</\s*li\s*>", "\n", html)

    # 2) Remove tags
    txt = strip_html(html) or ""

    # 3) Normalizações
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = re.sub(r"[ \t]+", " ", txt)        # espaços repetidos
    txt = re.sub(r"\n[ \t]+", "\n", txt)     # espaços no começo da linha

    # 4) Evitar "colado" clássico: "...AdolescenteA presente..."
    # Insere espaço quando há letra minúscula/maiúscula colada (camel-case acidental)
    txt = re.sub(r"([a-záéíóúàâêôãõç])([A-ZÁÉÍÓÚÀÂÊÔÃÕÇ])", r"\1 \2", txt)

    # 5) Compacta múltiplas linhas em branco
    txt = re.sub(r"\n{3,}", "\n\n", txt)

    txt = txt.strip()

    # 6) Trunca no limite
    if len(txt) > MAX_VARCHAR_4000:
        txt = txt[:MAX_VARCHAR_4000].rstrip()

    return txt

@frappe.whitelist()
def export_material_request_bionexo_xml(material_request: str):
    doc = frappe.get_doc("Material Request", material_request)

    if doc.docstatus != 1:
        frappe.throw("Somente é permitido exportar Material Request submetido (docstatus=1).")

    if not doc.items:
        frappe.throw("Material Request sem itens. Nada a exportar.")

    # Regras solicitadas
    requisicao = _make_requisicao_10_digits()
    titulo_pdc = (doc.title or "").strip()
    if not titulo_pdc:
        frappe.throw("Material Request sem título (title). Preencha o campo Título para exportar ao Bionexo.")

    observacao = doc.name  # doc.name preservado aqui
    termo = _sanitize_varchar_4000(doc.terms or "")

    data_vencimento = _fmt_date_ddmmyyyy(add_days(nowdate(), 2))
    hora_vencimento = HORA_VENCIMENTO_FIXA

    # --- XML conforme layout WA ---
    pedido = Element("Pedido")
    pedido.set("layout", LAYOUT)

    cab = SubElement(pedido, "Cabecalho")
    SubElement(cab, "Requisicao").text = requisicao
    SubElement(cab, "Titulo_Pdc").text = str(titulo_pdc)
    SubElement(cab, "Id_Forma_Pagamento").text = ID_FORMA_PAGAMENTO_FIXO
    SubElement(cab, "Data_Vencimento").text = str(data_vencimento)
    SubElement(cab, "Hora_Vencimento").text = str(hora_vencimento)
    SubElement(cab, "Moeda").text = MOEDA_FIXA
    SubElement(cab, "Observacao").text = _sanitize_varchar_4000(observacao)
    SubElement(cab, "Termo").text = termo
    SubElement(cab, "Tipo_Cotacao").text = TIPO_COTACAO_FIXO
    SubElement(cab, "Cod_Estoque").text = COD_ESTOQUE_FIXO

    itens_req = SubElement(pedido, "Itens_Requisicao")

    for it in doc.items:
        if not it.item_code:
            frappe.throw(f"Item (linha {it.idx}) sem item_code. Não é possível exportar Bionexo.")
        if not it.qty or float(it.qty) <= 0:
            frappe.throw(f"Item {it.item_code} (linha {it.idx}) com qty inválida ({it.qty}).")

        item_el = SubElement(itens_req, "Item_Requisicao")
        SubElement(item_el, "Codigo_Produto").text = str(it.item_code)
        SubElement(item_el, "Quantidade").text = _to_int_string(it.qty)

    xml_bytes = tostring(pedido, encoding="utf-8", method="xml")
    filename = f"BIONEXO_{doc.name}.xml"

    frappe.response["filename"] = filename
    frappe.response["filecontent"] = xml_bytes
    frappe.response["type"] = "download"
