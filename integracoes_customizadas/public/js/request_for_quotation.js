frappe.ui.form.on("Request for Quotation", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Exportar XML Bionexo"), () => {
			open_url_post(
				"/api/method/integracoes_customizadas.bionexo.export_xml.export_request_for_quotation_bionexo_xml",
				{ request_for_quotation: frm.doc.name }
			);
		}, __("Actions"));
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Importar PDF Bionexo"), () => {
				frappe.new_doc("Importacao Bionexo", { request_for_quotation: frm.doc.name });
			}, __("Actions"));
		}
		frm.add_custom_button(
			__("Mapa de Preços"),
			() => {
				frappe.set_route("query-report", "Mapa de Precos RFQ").then(() => {
					frappe.query_report.set_filter_value({ request_for_quotation: frm.doc.name });
				});
			},
			__("View")
		);
	},
});
