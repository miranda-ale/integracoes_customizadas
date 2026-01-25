frappe.ui.form.on("Solicitacao de Servico", {
	setup(frm) {
		frm.set_query("item", "itens", () => ({
			filters: {
				is_stock_item: 0
			}
		}));
	},
	onload(frm) {
		if (!frm.doc.data_solicitacao) {
			frm.set_value("data_solicitacao", frappe.datetime.nowdate());
		}
	},
	refresh(frm) {
		if (!frm.is_new() && frm.doc.docstatus < 2) {
			frm.add_custom_button("Criar Pesquisa de Preços", () => {
				frappe.new_doc("Pesquisa de Precos", {
					solicitacao_de_servico: frm.doc.name
				});
			});
		}
	}
});
