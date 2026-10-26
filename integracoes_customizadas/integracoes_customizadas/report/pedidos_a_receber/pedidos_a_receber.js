frappe.query_reports["Pedidos a Receber"] = {
	filters: [
		{ fieldname: "company", label: __("Empresa"), fieldtype: "Link", options: "Company" },
		{ fieldname: "supplier", label: __("Fornecedor"), fieldtype: "Link", options: "Supplier" },
		{ fieldname: "from_date", label: __("Emitidos a partir de"), fieldtype: "Date" },
		{ fieldname: "somente_atrasados", label: __("Somente atrasados"), fieldtype: "Check" },
	],
	formatter(value, row, column, data, default_formatter) {
		if (column.fieldname === "acao" && data && data.purchase_order) {
			return `<button class="btn btn-xs btn-primary cmp-receber" data-name="${frappe.utils.escape_html(
				data.purchase_order
			)}">${__("Receber")}</button>`;
		}
		if (column.fieldname === "atraso" && data && data.atraso) {
			return `<span class="text-danger">${data.atraso}</span>`;
		}
		return default_formatter(value, row, column, data);
	},
	onload(report) {
		// "Receber" opens a Purchase Receipt mapped from the order (quantities pending), ready to be filled in.
		report.page.main.off("click.cmp").on("click.cmp", ".cmp-receber", function () {
			frappe.model.open_mapped_doc({
				method: "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt",
				source_name: $(this).data("name"),
			});
		});
	},
};
