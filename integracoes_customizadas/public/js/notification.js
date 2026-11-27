// Destinatários da Notification: com WhatsApp ativo, o Select "receiver_by_document_field" também lista
// campos Phone do documento (o core só lista Email/User no canal Email). O valor que não for um User é
// tratado como telefone em whatsapp/notification.py.
frappe.ui.form.on("Notification", {
	refresh: (frm) => add_phone_receivers(frm),
	document_type: (frm) => add_phone_receivers(frm),
	channel: (frm) => add_phone_receivers(frm),
	send_whatsapp: (frm) => add_phone_receivers(frm),
});

function add_phone_receivers(frm) {
	if (!frm.doc.document_type || !frm.doc.send_whatsapp) return;
	// roda depois do handler do core, que também define as opções de forma assíncrona
	frappe.model.with_doctype(frm.doc.document_type, () => {
		setTimeout(() => {
			const grid = frm.fields_dict.recipients && frm.fields_dict.recipients.grid;
			if (!grid) return;
			const option = (df, parent) => ({
				value: parent ? `${df.fieldname},${parent.fieldname}` : df.fieldname,
				label: `${df.label || df.fieldname} (${df.fieldname}${
					parent ? ` / ${parent.fieldname}` : ""
				})`,
			});
			const found = [];
			frappe.get_meta(frm.doc.document_type).fields.forEach((df) => {
				if (df.fieldtype === "Data" && df.options === "Phone") found.push(option(df));
				else if (frappe.model.table_fields.includes(df.fieldtype)) {
					frappe.model.with_doctype(df.options, () => {
						frappe.get_meta(df.options).fields.forEach((child) => {
							if (child.fieldtype === "Data" && child.options === "Phone") {
								found.push(option(child, df));
							}
						});
						merge(grid, found);
					});
				}
			});
			merge(grid, found);
		}, 300);
	});
}

function merge(grid, found) {
	const df = grid.get_docfield("receiver_by_document_field");
	const current = (df.options || "").split("\n");
	const known = new Set(current.map((o) => o.split("|")[0]));
	const extra = found.filter((o) => !known.has(o.value)).map((o) => o.value);
	if (!extra.length) return;
	grid.update_docfield_property(
		"receiver_by_document_field",
		"options",
		current.filter((o) => o !== "").concat(extra)
	);
}
