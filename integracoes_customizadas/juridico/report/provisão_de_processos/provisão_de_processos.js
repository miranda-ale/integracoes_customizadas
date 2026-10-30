frappe.query_reports["Provisão de Processos"] = {
	filters: [
		{ fieldname: "company", label: __("Empresa"), fieldtype: "Link", options: "Company" },
		{ fieldname: "natureza", label: __("Natureza"), fieldtype: "Select", options: "\nTrabalhista\nCível\nTributário\nOutros" },
		{ fieldname: "status_processo", label: __("Situação"), fieldtype: "Select", options: "\nEm andamento\nEncerrado", default: "Em andamento" },
		{ fieldname: "risco", label: __("Risco"), fieldtype: "Select", options: "\nBaixo\nMédio\nAlto" },
		{ fieldname: "probabilidade_perda", label: __("Probabilidade de Perda"), fieldtype: "Select", options: "\nProvável\nPossível\nRemota" },
	],
};
