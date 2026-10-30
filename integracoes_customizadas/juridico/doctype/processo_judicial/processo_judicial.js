frappe.ui.form.on("Processo Judicial", {
	refresh(frm) {
		// Máscara de CPF/CNPJ ao digitar (helper do app busca_cnpj).
		if (window.busca_cnpj?.taxid) busca_cnpj.taxid.bind_input(frm.fields_dict.cpf_parte);
		if (frm.is_new() || !frm.perm[0]?.write) return;
		frm.add_custom_button(__("Buscar andamentos"), () => {
			if (frm.is_dirty()) {
				frappe.msgprint(__("Salve as alterações antes de buscar andamentos."));
				return;
			}
			frappe.call({
				method: "integracoes_customizadas.juridico.datajud.buscar_andamentos",
				args: { processo: frm.doc.name },
				freeze: true,
				freeze_message: __("Consultando o DataJud. Aguarde..."),
				callback(response) {
					if (response.exc) return;
					const novos = response.message.novos_andamentos;
					frappe.show_alert(
						{
							message:
								novos === 1
									? __("1 novo andamento encontrado.")
									: novos > 1
									? __("{0} novos andamentos encontrados.", [novos])
									: __("Nenhum andamento novo encontrado."),
							indicator: novos ? "green" : "blue",
						},
						8
					);
					frm.reload_doc();
				},
			});
		});
	},
	tipo_parte(frm) {
		frm.set_value("parte", "");
		frm.set_value(
			"doctype_parte",
			frm.doc.tipo_parte === "Terceiros" ? "Contact" : frm.doc.tipo_parte
		);
	},
});

frappe.ui.form.on("Processo Judicial Parte", {
	tipo_parte(frm, cdt, cdn) {
		const linha = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "parte", "");
		frappe.model.set_value(
			cdt,
			cdn,
			"doctype_parte",
			linha.tipo_parte === "Terceiros" ? "Contact" : linha.tipo_parte
		);
	},
	principal(frm, cdt, cdn) {
		// Apenas uma parte principal: marcar uma desmarca as demais.
		if (!locals[cdt][cdn].principal) return;
		frm.doc.partes.forEach((linha) => {
			if (linha.name !== cdn && linha.principal) {
				frappe.model.set_value(linha.doctype, linha.name, "principal", 0);
			}
		});
	},
	form_render(frm, cdt, cdn) {
		if (window.busca_cnpj?.taxid) {
			busca_cnpj.taxid.bind_input(frm.fields_dict.partes.grid.get_row(cdn).grid_form.fields_dict.documento);
		}
	},
});
