// Feedback imediato da regra de caixa alta (a garantia real é o hook de servidor em normalizacao/maiusculas.py)
(() => {
	const CAMPOS = {
		Employee: ["first_name", "middle_name", "last_name"],
		Company: ["company_name"],
		Supplier: ["supplier_name"],
		Customer: ["customer_name"],
		Item: ["item_name"],
		Contact: ["first_name", "middle_name", "last_name"],
		Address: ["address_title"],
		Lead: ["lead_name", "first_name", "middle_name", "last_name", "company_name"],
		Department: ["department_name"],
		Designation: ["designation_name"],
	};
	const normalizar = (v) =>
		v.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/\s+/g, " ").trim().toUpperCase();

	Object.entries(CAMPOS).forEach(([doctype, campos]) => {
		const handlers = {};
		campos.forEach((campo) => {
			handlers[campo] = (frm) => {
				const v = frm.doc[campo];
				if (v && typeof v === "string" && normalizar(v) !== v)
					frm.set_value(campo, normalizar(v));
			};
		});
		frappe.ui.form.on(doctype, handlers);
	});
})();
