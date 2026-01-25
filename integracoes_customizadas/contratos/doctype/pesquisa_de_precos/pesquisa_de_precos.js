frappe.ui.form.on("Pesquisa de Precos", {
	setup(frm) {
		frm.set_query("item", "itens", () => ({
			filters: {
				is_stock_item: 0
			}
		}));
	},
	refresh(frm) {
		if (frm.doc.solicitacao_de_servico && frm.doc.itens.length === 0) {
			frm.add_custom_button("Carregar Itens da Solicitação", () => {
				frappe.db.get_doc("Solicitacao de Servico", frm.doc.solicitacao_de_servico).then((doc) => {
					frm.clear_table("itens");
					(doc.itens || []).forEach((item) => {
						const row = frm.add_child("itens");
						row.item = item.item;
						row.descricao = item.descricao;
						row.quantidade = item.quantidade;
						row.uom = item.uom;
					});
					frm.refresh_field("itens");
				});
			});
		}
	}
});
