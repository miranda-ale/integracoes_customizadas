frappe.query_reports["Aging de Processos"] = {
	filters: [
		{ fieldname: "company", label: __("Empresa"), fieldtype: "Link", options: "Company" },
		{ fieldname: "natureza", label: __("Natureza"), fieldtype: "Select", options: "\nTrabalhista\nCível\nTributário\nOutros" },
		{ fieldname: "risco", label: __("Risco"), fieldtype: "Select", options: "\nBaixo\nMédio\nAlto" },
	],
};
