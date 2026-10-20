// Instância-alvo das ações: a principal ou uma das adicionais ativas (pergunta só se houver mais de uma).
function com_instancia(frm, acao) {
	const nomes = [frm.doc.instance_name].concat(
		(frm.doc.instancias || []).filter((l) => l.ativo && l.instance_name).map((l) => l.instance_name)
	);
	if (nomes.length === 1) return acao(nomes[0]);
	frappe.prompt(
		{ fieldname: "instancia", fieldtype: "Select", label: __("Instância"), options: nomes, default: nomes[0], reqd: 1 },
		(valores) => acao(valores.instancia),
		__("Escolha a instância")
	);
}

frappe.ui.form.on("Configuracoes WhatsApp", {
	refresh(frm) {
		const area = frm.fields_dict.connection_html.$wrapper;
		area.empty();
		if (frm.is_new() || !frm.doc.server_url || !frm.doc.instance_name) {
			area.text(__("Salve a configuração para consultar a conexão."));
			return;
		}
		frm.add_custom_button(__("Criar instância"), () => com_instancia(frm, (instancia) => {
			frappe.call({
				method: "integracoes_customizadas.whatsapp.api.create_instance",
				args: { instancia },
				freeze: true,
				freeze_message: __("Criando instância na Evolution API..."),
				callback: (r) => {
					const created = r.message?.created;
					frappe.show_alert(
						{
							message: created
								? __("Instância {0} criada. Gere o QR Code para conectar.", [r.message.instance_name])
								: __("A instância {0} já existe na Evolution API.", [r.message?.instance_name]),
							indicator: created ? "green" : "blue",
						},
						7
					);
					frm.trigger("show_status");
				},
				error: () => frm.trigger("show_status"),
			});
		}));
		frm.add_custom_button(__("Atualizar estado"), () => frm.trigger("show_status"));
		frm.add_custom_button(__("Gerar novo QR Code"), () => com_instancia(frm, (instancia) => {
			frappe.call({
				method: "integracoes_customizadas.whatsapp.api.get_qr_code",
				args: { instancia },
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
		}));
		frm.trigger("show_status");
	},
	show_status(frm) {
		frappe.call({
			method: "integracoes_customizadas.whatsapp.api.get_connection_state",
			type: "GET",
			callback: (r) => {
				const estados = r.message?.instancias || {};
				const nomes = Object.keys(estados);
				frm.fields_dict.connection_html.$wrapper.text(
					nomes.length > 1
						? __("Estado da conexão: {0}", [nomes.map((n) => `${n}: ${estados[n]}`).join(" · ")])
						: __("Estado da conexão: {0}", [r.message?.state || __("desconhecido")])
				);
			},
		});
	},
});
