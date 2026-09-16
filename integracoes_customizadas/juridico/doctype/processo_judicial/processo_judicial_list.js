frappe.listview_settings["Processo Judicial"] = {
	onload(listview) {
		const abrir_resultado = (resultado) => {
			if (resultado.existente) {
				frappe.show_alert({ message: __("Processo já cadastrado. Abrindo o registro existente."), indicator: "blue" });
				frappe.set_route("Form", "Processo Judicial", resultado.name);
				return;
			}

			frappe.model.with_doctype("Processo Judicial", () => {
				const doc = frappe.model.get_new_doc("Processo Judicial");
				for (const [fieldname, value] of Object.entries(resultado.doc)) {
					if (fieldname === "assuntos" || fieldname === "movimentos") {
						for (const linha of value || []) {
							const child = frappe.model.add_child(doc, fieldname);
							for (const [campo, valor] of Object.entries(linha)) {
								if (frappe.meta.has_field(child.doctype, campo)) child[campo] = valor;
							}
						}
					} else if (frappe.meta.has_field(doc.doctype, fieldname)) {
						doc[fieldname] = value;
					}
				}
				frappe.show_alert({ message: __("Consulta concluída. Revise os dados e salve o processo para cadastrá-lo."), indicator: "green" }, 8);
				frappe.set_route("Form", doc.doctype, doc.name);
			});
		};

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
								freeze: true,
								freeze_message: __("Consultando o DataJud. Aguarde..."),
								callback(result) {
									if (result.exc) return;
									const ocorrencias = result.message || [];
									if (ocorrencias.length) {
										dialog.hide();
										if (ocorrencias.length === 1) {
											abrir_resultado(ocorrencias[0]);
										} else {
											const escolhas = ocorrencias.map((item, indice) => ({
												label: `${indice + 1}. ${item.existente ? item.name : item.doc.datajud_id}`,
												value: String(indice),
											}));
											frappe.prompt([{ fieldname: "ocorrencia", fieldtype: "Select", label: __("Ocorrência"), options: escolhas, reqd: 1 }],
												(selecao) => abrir_resultado(ocorrencias[Number(selecao.ocorrencia)]),
												__("Selecione a ocorrência"), __("Abrir"));
										}
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
