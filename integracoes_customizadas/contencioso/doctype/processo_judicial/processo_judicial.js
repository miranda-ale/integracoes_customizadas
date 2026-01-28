frappe.ui.form.on("Processo Judicial", {
	refresh(frm) {
		apply_party_masking(frm);
		apply_confidential_filter(frm);
	},
	cj_partes_on_form_rendered(frm) {
		apply_party_masking(frm);
	},
	cj_documentos_on_form_rendered(frm) {
		apply_confidential_filter(frm);
	},
});

function is_legal_user() {
	return frappe.user.has_role("CJ Administrador")
		|| frappe.user.has_role("CJ Gestor Jurídico")
		|| frappe.user.has_role("CJ Analista Jurídico");
}

function mask_doc_id(value) {
	if (!value) return value;
	const digits = value.replace(/\D/g, "");
	if (digits.length === 11) {
		return `${digits.slice(0, 3)}.***.***-${digits.slice(-2)}`;
	}
	if (digits.length === 14) {
		return `${digits.slice(0, 2)}.***.***/****-${digits.slice(-2)}`;
	}
	return value;
}

function apply_party_masking(frm) {
	if (is_legal_user()) return;
	const grid = frm.fields_dict?.cj_partes?.grid;
	if (!grid) return;
	const field = grid.get_field("nome_da_parte");
	if (!field) return;

	field.formatter = (value) => mask_doc_id(value);
	grid.refresh();
}

function apply_confidential_filter(frm) {
	if (is_legal_user()) return;
	const grid = frm.fields_dict?.cj_documentos?.grid;
	if (!grid) return;
	(grid.grid_rows || []).forEach((row) => {
		if (row?.doc?.cj_confidencial) {
			row.toggle(false);
		} else {
			row.toggle(true);
		}
	});
}
