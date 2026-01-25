frappe.ui.form.on("Resultado de Contratacao", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.docstatus < 2) {
			frm.add_custom_button("Criar Contrato", () => {
				frappe.new_doc("Contrato de Servico", {
					resultado_de_contratacao: frm.doc.name,
					fornecedor: frm.doc.fornecedor_vencedor
				});
			});
		}
	}
});
