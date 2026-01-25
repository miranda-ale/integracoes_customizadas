frappe.ui.form.on("Contrato de Servico", {
	setup(frm) {
		frm.set_query("item", "itens", () => ({
			filters: {
				is_stock_item: 0
			}
		}));
	},
	refresh(frm) {
		if (!frm.is_new() && frm.doc.docstatus < 2) {
			if (!frm.doc.purchase_order) {
				frm.add_custom_button("Gerar Purchase Order", () => {
					frappe.call({
						method: "integracoes_customizadas.contratos.doctype.contrato_de_servico.contrato_de_servico.criar_purchase_order",
						args: { contrato: frm.doc.name },
						callback: (r) => {
							if (r.message) {
								frm.set_value("purchase_order", r.message);
								frappe.set_route("Form", "Purchase Order", r.message);
							}
						}
					});
				});
			}

			if (frm.doc.purchase_order && !frm.doc.purchase_invoice) {
				frm.add_custom_button("Gerar Purchase Invoice", () => {
					frappe.call({
						method: "integracoes_customizadas.contratos.doctype.contrato_de_servico.contrato_de_servico.criar_purchase_invoice",
						args: { contrato: frm.doc.name },
						callback: (r) => {
							if (r.message) {
								frm.set_value("purchase_invoice", r.message);
								frappe.set_route("Form", "Purchase Invoice", r.message);
							}
						}
					});
				});
			}
		}
	}
});
