frappe.ui.form.on("Request for Quotation", {
	refresh(frm) {
		if (frm.is_new()) return;
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
