frappe.ui.form.on("Envio WhatsApp", {
	refresh(frm) {
		if (frm.doc.status !== "Falhou" || frm.is_new()) return;
		frm.add_custom_button(__("Reenviar"), () => {
			frappe.call({
				method: "integracoes_customizadas.whatsapp.api.retry_delivery",
				args: { delivery_name: frm.doc.name },
				callback: () => frm.reload_doc(),
			});
		});
	},
});
