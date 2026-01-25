import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice


class ContratodeServico(Document):
	def validate(self):
		if self.data_inicio and self.data_fim:
			if getdate(self.data_fim) < getdate(self.data_inicio):
				frappe.throw("A data de término não pode ser anterior à data de início.")


@frappe.whitelist()
def criar_purchase_order(contrato):
	contrato_doc = frappe.get_doc("Contrato de Servico", contrato)

	if not contrato_doc.fornecedor:
		frappe.throw("Informe o fornecedor antes de gerar a Purchase Order.")

	if not contrato_doc.empresa:
		frappe.throw("Informe a empresa antes de gerar a Purchase Order.")

	if not contrato_doc.itens:
		frappe.throw("Inclua ao menos um item no contrato para gerar a Purchase Order.")

	po = frappe.new_doc("Purchase Order")
	po.company = contrato_doc.empresa
	po.supplier = contrato_doc.fornecedor
	po.transaction_date = nowdate()
	po.schedule_date = contrato_doc.data_inicio or nowdate()

	for item in contrato_doc.itens:
		uom = item.uom or frappe.db.get_value("Item", item.item, "stock_uom")
		qty = item.quantidade or 1
		rate = item.valor_unitario or 0
		po.append(
			"items",
			{
				"item_code": item.item,
				"qty": qty,
				"uom": uom,
				"rate": rate,
				"schedule_date": contrato_doc.data_inicio or nowdate(),
				"cost_center": item.centro_custo or contrato_doc.centro_custo,
			},
		)

	po.flags.ignore_permissions = True
	po.insert()

	contrato_doc.purchase_order = po.name
	contrato_doc.save(ignore_permissions=True)

	return po.name


@frappe.whitelist()
def criar_purchase_invoice(contrato):
	contrato_doc = frappe.get_doc("Contrato de Servico", contrato)

	if not contrato_doc.purchase_order:
		frappe.throw("Crie a Purchase Order antes de gerar a Purchase Invoice.")

	pi = make_purchase_invoice(contrato_doc.purchase_order)
	pi.flags.ignore_permissions = True
	pi.insert()

	contrato_doc.purchase_invoice = pi.name
	contrato_doc.save(ignore_permissions=True)

	return pi.name
