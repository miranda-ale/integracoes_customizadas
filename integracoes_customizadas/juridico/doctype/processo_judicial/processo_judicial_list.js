frappe.listview_settings["Processo Judicial"] = {
	onload(listview) {
		frappe.call({
			method: "integracoes_customizadas.juridico.datajud.listar_tribunais",
			callback(response) {
				const tribunais = response.message || [];
				const abrir_dialogo = () => {
					const dialog = new frappe.ui.Dialog({
						title: __("Acompanhar processo"),
						fields: [
							{
								fieldname: "numero_processo",
								fieldtype: "Data",
								label: __("Número CNJ"),
								reqd: 1,
							},
							{
								fieldname: "tribunal_alias",
								fieldtype: "Select",
								label: __("Tribunal"),
								options: [
									{ label: __("Selecione um tribunal"), value: "" },
									...tribunais.map((item) => ({ label: item.label, value: item.value })),
								],
								reqd: 1,
							},
						],
						primary_action_label: __("Consultar e acompanhar"),
						primary_action(values) {
							dialog.disable_primary_action();
							frappe.call({
								method: "integracoes_customizadas.juridico.datajud.acompanhar_processo",
								args: values,
								callback(result) {
									const nomes = result.message || [];
									if (nomes.length) {
										dialog.hide();
										listview.refresh();
										frappe.show_alert({ message: __("{0} ocorrência(s) acompanhada(s).", [nomes.length]), indicator: "green" });
										frappe.set_route("Form", "Processo Judicial", nomes[0]);
									} else {
										frappe.msgprint(__("Nenhuma ocorrência encontrada para esse número e tribunal."));
									}
								},
								always() {
									dialog.enable_primary_action();
								},
							});
						},
					});
					dialog.show();
					const input = dialog.get_field("numero_processo").$input;
				input.attr("maxlength", 25);
				input.on("input", () => {
						const digits = input.val().replace(/\D/g, "").slice(0, 20);
						let masked = digits.slice(0, 7);
						if (digits.length > 7) masked += "-" + digits.slice(7, 9);
						if (digits.length > 9) masked += "." + digits.slice(9, 13);
						if (digits.length > 13) masked += "." + digits.slice(13, 14);
						if (digits.length > 14) masked += "." + digits.slice(14, 16);
						if (digits.length > 16) masked += "." + digits.slice(16, 20);
						input.val(masked);
					});
				};
				listview.set_primary_action = () => {
					listview.page.set_primary_action(__("Acompanhar processo"), abrir_dialogo, "add");
				};
				listview.set_primary_action();
			},
		});
	},
};
