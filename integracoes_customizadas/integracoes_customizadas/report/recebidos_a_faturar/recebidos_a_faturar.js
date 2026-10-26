frappe.query_reports["Recebidos a Faturar"] = {
	filters: [
		{ fieldname: "company", label: __("Empresa"), fieldtype: "Link", options: "Company" },
		{ fieldname: "supplier", label: __("Fornecedor"), fieldtype: "Link", options: "Supplier" },
		{ fieldname: "somente_com_nf", label: __("Somente com NF informada"), fieldtype: "Check" },
	],
	formatter(value, row, column, data, default_formatter) {
		if (!data) return default_formatter(value, row, column, data);
		if (column.fieldname === "acao") {
			return `<button class="btn btn-xs btn-primary cmp-faturar" data-name="${frappe.utils.escape_html(
				data.purchase_receipt
			)}">${__("Criar Fatura")}</button>`;
		}
		if (column.fieldname === "situacao_nf") {
			const cls = data.situacao_nf === "Pendente" ? "text-danger" : "text-success";
			return `<span class="${cls}">${__(data.situacao_nf)}</span>`;
		}
		if (
			column.fieldname === "nf_anexo" &&
			data.nf_anexo &&
			String(data.nf_anexo).startsWith("/")
		) {
			const url = frappe.utils.escape_html(data.nf_anexo);
			return `<a href="${url}" target="_blank" rel="noopener">${__("Abrir")}</a>`;
		}
		if (column.fieldname === "diferenca" && data.diferenca) {
			return `<span class="text-warning">${default_formatter(
				value,
				row,
				column,
				data
			)}</span>`;
		}
		return default_formatter(value, row, column, data);
	},
	onload(report) {
		// "Criar Fatura" opens a Purchase Invoice mapped from the receipt; bill_no/bill_date come from its NF.
		report.page.main.off("click.cmp").on("click.cmp", ".cmp-faturar", function () {
			frappe.model.open_mapped_doc({
				method: "erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice",
				source_name: $(this).data("name"),
			});
		});
	},
};
