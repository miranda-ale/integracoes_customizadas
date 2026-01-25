frappe.ui.form.on("Edital de Contratacao", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.docstatus < 2) {
			frm.add_custom_button("Registrar Resultado", () => {
				frappe.new_doc("Resultado de Contratacao", {
					edital_de_contratacao: frm.doc.name,
					solicitacao_de_servico: frm.doc.solicitacao_de_servico
				});
			});
		}
	}
});
