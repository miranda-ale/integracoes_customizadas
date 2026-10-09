frappe.ui.form.on("Configuracoes WhatsApp", {
	refresh(frm) {
		const area = frm.fields_dict.connection_html.$wrapper;
		area.empty();
		if (frm.is_new() || !frm.doc.server_url || !frm.doc.instance_name) {
			area.text(__("Salve a configuração para consultar a conexão."));
			return;
		}
		frm.add_custom_button(__("Criar instância"), () => {
			frappe.call({
				method: "integracoes_customizadas.whatsapp.api.create_instance",
				freeze: true,
				callback: () => frm.trigger("show_status"),
			});
		});
		frm.add_custom_button(__("Atualizar estado"), () => frm.trigger("show_status"));
		frm.add_custom_button(__("Gerar novo QR Code"), () => {
			frappe.call({
				method: "integracoes_customizadas.whatsapp.api.get_qr_code",
				callback: (r) => {
					area.empty();
					if (r.message?.state === "open") {
						area.text(__("WhatsApp conectado."));
					} else if (r.message?.image) {
						$("<p>").text(__("Escaneie com o WhatsApp em Aparelhos conectados.")).appendTo(area);
						$("<img>", { src: r.message.image, alt: __("QR Code de conexão") })
							.css({ width: "260px", height: "260px" }).appendTo(area);
					} else {
						area.text(__("QR Code indisponível. Tente novamente em alguns segundos."));
					}
				},
			});
		});
		frm.trigger("show_status");
	},
	show_status(frm) {
		frappe.call({
			method: "integracoes_customizadas.whatsapp.api.get_connection_state",
			type: "GET",
			callback: (r) => {
				frm.fields_dict.connection_html.$wrapper.text(
					__("Estado da conexão: {0}", [r.message?.state || __("desconhecido")])
				);
			},
		});
	},
});
