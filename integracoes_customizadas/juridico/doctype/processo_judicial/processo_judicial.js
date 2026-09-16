frappe.ui.form.on("Processo Judicial", {
	refresh(frm) {
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
					frappe.show_alert({
						message: novos === 1
							? __("1 novo andamento encontrado.")
							: novos > 1
								? __("{0} novos andamentos encontrados.", [novos])
								: __("Nenhum andamento novo encontrado."),
						indicator: novos ? "green" : "blue",
					}, 8);
					frm.reload_doc();
				},
			});
		});
	},
	tipo_parte(frm) {
		frm.set_value("parte", "");
		frm.set_value("doctype_parte", frm.doc.tipo_parte === "Terceiros" ? "Contact" : frm.doc.tipo_parte);
	},
});
