// Copyright (c) 2026, BHCL and contributors
// For license information, please see license.txt

const METODOS = "integracoes_customizadas.bionexo.importacao";

frappe.ui.form.on("Importacao Bionexo", {
	setup(frm) {
		frm.set_query("material_request", () => ({
			filters: { docstatus: 1, material_request_type: "Purchase" },
		}));
		frm.set_query("request_for_quotation", () => ({
			query: `${METODOS}.rfq_por_material_request`,
			filters: { material_request: frm.doc.material_request || "" },
		}));
		frm.set_query("item_code", "itens", () => ({
			filters: { name: ["in", frm.__itens_rfq || []] },
		}));
	},

	refresh(frm) {
		carregar_vinculos(frm);
		montar_resumo(frm);

		if (frm.doc.docstatus === 0 && !frm.is_new()) {
			frm.add_custom_button(__("Ler PDF novamente"), () => {
				frappe.confirm(
					__("Reler o PDF descarta os itens relacionados manualmente. Continuar?"),
					() => frm.call("reanalisar").then(() => frm.reload_doc())
				);
			});
			const pendentes = (frm.doc.fornecedores || []).filter((f) => !f.supplier);
			if (pendentes.length) {
				frm.add_custom_button(__("Cadastrar fornecedores pendentes ({0})", [pendentes.length]), () =>
					cadastrar_fornecedores(frm)
				);
			}
		}

		if (frm.doc.docstatus === 1) {
			const docs = (campo) => [...new Set((frm.doc.cotacoes || []).map((c) => c[campo]).filter(Boolean))];
			frm.add_custom_button(
				__("Orçamentos de Fornecedor"),
				() => frappe.set_route("List", "Supplier Quotation", { name: ["in", docs("supplier_quotation")] }),
				__("View")
			);
			if (docs("purchase_order").length) {
				frm.add_custom_button(
					__("Ordens de Compra"),
					() => frappe.set_route("List", "Purchase Order", { name: ["in", docs("purchase_order")] }),
					__("View")
				);
			}
		}
	},

	request_for_quotation(frm) {
		frm.__itens_rfq = [];
		if (!frm.doc.request_for_quotation) return;
		carregar_vinculos(frm).then((vinculos) => {
			// Um Pedido de Cotação referencia uma só Solicitação de Compras: preenche automaticamente.
			if (vinculos && vinculos.material_requests.length === 1) {
				frm.set_value("material_request", vinculos.material_requests[0]);
			}
		});
	},

	material_request(frm) {
		if (!frm.doc.material_request || !frm.doc.request_for_quotation) return;
		carregar_vinculos(frm).then((vinculos) => {
			if (vinculos && !vinculos.material_requests.includes(frm.doc.material_request)) {
				frm.set_value("request_for_quotation", "");
			}
		});
	},
});

frappe.ui.form.on("Importacao Bionexo Item", {
	item_code(frm, cdt, cdn) {
		const linha = locals[cdt][cdn];
		if (linha.item_code && linha.ignorar) frappe.model.set_value(cdt, cdn, "ignorar", 0);
	},
});

function carregar_vinculos(frm) {
	if (!frm.doc.request_for_quotation) return Promise.resolve(null);
	return frappe
		.xcall(`${METODOS}.vinculos_da_rfq`, { request_for_quotation: frm.doc.request_for_quotation })
		.then((vinculos) => {
			frm.__itens_rfq = vinculos.item_codes;
			return vinculos;
		});
}

function cadastrar_fornecedores(frm) {
	frappe.dom.freeze(__("Consultando CNPJs e cadastrando fornecedores..."));
	frappe
		.xcall(`${METODOS}.criar_fornecedores`, { importacao: frm.doc.name })
		.then((r) => {
			let mensagem = __("{0} fornecedor(es) cadastrado(s).", [r.criados.length]);
			if (r.erros.length) mensagem += "<br><br>" + __("Falhas:") + "<br>" + r.erros.join("<br>");
			frappe.msgprint({ message: mensagem, indicator: r.erros.length ? "orange" : "green" });
			frm.reload_doc();
		})
		.finally(() => frappe.dom.unfreeze());
}

function montar_resumo(frm) {
	const campo = frm.get_field("resumo_html");
	if (!campo) return;
	const doc = frm.doc;
	if (!(doc.itens || []).length) {
		campo.$wrapper.html(`<p class="text-muted">${__("Anexe o relatório PDF do Bionexo e salve.")}</p>`);
		return;
	}
	const itens_pendentes = doc.itens.filter((i) => i.situacao === "Não identificado").length;
	const fornecedores_pendentes = (doc.fornecedores || []).filter((f) => !f.supplier).length;
	const totais = {};
	(doc.cotacoes || [])
		.filter((c) => c.status_bionexo === "Confirmado")
		.forEach((c) => {
			const chave = c.supplier || c.nome_bionexo;
			totais[chave] = (totais[chave] || 0) + flt(c.amount);
		});
	const linhas = Object.entries(totais)
		.map(
			([fornecedor, total]) =>
				`<tr><td>${frappe.utils.escape_html(fornecedor)}</td><td class="text-right">${format_currency(total)}</td></tr>`
		)
		.join("");
	const indicador = (n, rotulo) =>
		`<span class="indicator-pill ${n ? "orange" : "green"}" style="margin-right: 8px">${rotulo}: ${n}</span>`;
	campo.$wrapper.html(`
		<div style="margin-bottom: 12px">
			<span class="indicator-pill blue" style="margin-right: 8px">${__("Itens")}: ${doc.itens.length}</span>
			<span class="indicator-pill blue" style="margin-right: 8px">${__("Fornecedores")}: ${(doc.fornecedores || []).length}</span>
			<span class="indicator-pill blue" style="margin-right: 8px">${__("Cotações")}: ${(doc.cotacoes || []).length}</span>
			${indicador(itens_pendentes, __("Itens não identificados"))}
			${indicador(fornecedores_pendentes, __("Fornecedores não cadastrados"))}
		</div>
		${
			linhas
				? `<table class="table table-bordered table-sm" style="max-width: 640px">
				<thead><tr><th>${__("Confirmados no Bionexo (geram Ordem de Compra)")}</th><th class="text-right">${__("Total")}</th></tr></thead>
				<tbody>${linhas}</tbody></table>`
				: `<p class="text-muted">${__("Nenhum item confirmado no Bionexo: só serão gerados Orçamentos de Fornecedor.")}</p>`
		}`);
}
