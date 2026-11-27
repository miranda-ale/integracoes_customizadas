frappe.query_reports["Integ Legal Cases by Employee"] = {
	filters: [
		{ fieldname: "company", label: __("Empresa"), fieldtype: "Link", options: "Company" },
		{
			fieldname: "natureza",
			label: __("Natureza"),
			fieldtype: "Select",
			options: "\nTrabalhista\nCível\nTributário\nOutros",
		},
		{
			fieldname: "status_processo",
			label: __("Situação"),
			fieldtype: "Select",
			options: "\nEm andamento\nEncerrado",
			default: "Em andamento",
		},
	],
};
