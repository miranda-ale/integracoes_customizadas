// Copyright (c) 2026, BHCL and contributors
// For license information, please see license.txt
//
// Adapted from the CLM "CLM Mapa de Precos" report, reading ERPNext Request for Quotation
// and the Supplier Quotations linked to it.

frappe.query_reports["Mapa de Precos RFQ"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
		{ fieldname: "from_date", label: __("Criada de"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("Criada até"), fieldtype: "Date" },
		{
			fieldname: "status_rfq",
			label: __("Status da Solicitação"),
			fieldtype: "Select",
			options: "\nDraft\nSubmitted\nCancelled",
		},
		{
			fieldname: "request_for_quotation",
			label: __("Request for Quotation"),
			fieldtype: "Link",
			options: "Request for Quotation",
			reqd: 1,
			// A lista de opções respeita os filtros acima
			get_query: function () {
				const v = (f) => frappe.query_report.get_filter_value(f);
				const filters = {};
				if (v("company")) filters.company = v("company");
				if (v("status_rfq")) filters.status = v("status_rfq");
				if (v("from_date") && v("to_date")) {
					filters.transaction_date = ["between", [v("from_date"), v("to_date")]];
				} else if (v("from_date")) {
					filters.transaction_date = [">=", v("from_date")];
				} else if (v("to_date")) {
					filters.transaction_date = ["<=", v("to_date")];
				}
				return { filters };
			},
		},
		{ fieldname: "include_discarded", label: __("Incluir canceladas/paralisadas"), fieldtype: "Check" },
		{ fieldname: "include_description", label: __("Incluir descrição do objeto"), fieldtype: "Check" },
		{ fieldname: "include_global_value", label: __("Incluir Valor Global"), fieldtype: "Check" },
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;
		if (data.is_total) value = `<strong>${value}</strong>`;
		// Destaca o(s) menor(es) preço(s) válido(s) da linha (e o menor total)
		if ((data.lowest_fields || []).includes(column.fieldname)) {
			// default_formatter envolve valores numéricos num <div>; remover para manter o marcador na mesma linha
			const valorInline = value.replace(/<\/?div[^>]*>/g, "");
			value = `<span style="background:#e6f4ea;color:#137333;font-weight:600;padding:1px 6px;border-radius:4px">▼ ${valorInline}</span>`;
		}
		return value;
	},
};
