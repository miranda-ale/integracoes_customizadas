// Etapas do processo de compras: barra recolhível no topo dos formulários da cadeia de materiais.
// Mesmo visual da barra do CLM; os status vêm de integracoes_customizadas.compras.process_view.get_purchase_steps.
/* global compras */
frappe.provide("compras.steps");

// Espelho de process_view.STAGES; usado antes de o documento ser salvo.
// [key, doctypes, label, group]: the quotation steps are optional and drawn inside one dashed group.
compras.steps.GROUP_LABELS = { cotacao: __("Cotação · opcional") };
compras.steps.STEPS = [
	["request", ["Material Request"], __("Solicitação de Compras")],
	["rfq", ["Request for Quotation"], __("Pedido de Cotação"), "cotacao"],
	["quotation", ["Supplier Quotation"], __("Cotação do Fornecedor"), "cotacao"],
	["order", ["Purchase Order"], __("Ordem de Compra")],
	["receipt", ["Purchase Receipt"], __("Recebimento de Compra")],
	["invoice", ["Purchase Invoice"], __("Nota Fiscal de Compra")],
];

compras.steps.STATUS_TEXT = {
	ok: __("Concluída"),
	pending: __("Em andamento"),
	warn: __("Atenção"),
	none: __("Não iniciada"),
};

compras.steps.STATUS_HELP = {
	ok: __("Todos os documentos desta etapa foram concluídos."),
	pending: __("Há documentos desta etapa ainda em andamento ou aguardando a etapa seguinte."),
	warn: __("Esta etapa exige atenção; veja os pontos abaixo."),
	none: __("Nenhum documento desta etapa foi criado ainda."),
};

compras.steps.STORAGE_KEY = "compras_steps_collapsed";

compras.steps.is_collapsed = function () {
	try {
		return window.localStorage.getItem(compras.steps.STORAGE_KEY) === "1";
	} catch (e) {
		return false;
	}
};

compras.steps.set_collapsed = function (value) {
	try {
		window.localStorage.setItem(compras.steps.STORAGE_KEY, value ? "1" : "0");
	} catch (e) {
		// Storage blocked: the bar simply opens expanded next time.
	}
};

compras.steps.stage_of = (doctype) =>
	compras.steps.STEPS.find((step) => step[1].includes(doctype))?.[0];

// Placeholder of a document not saved yet: only the current step is known.
compras.steps.local_model = function (frm) {
	return {
		current: compras.steps.stage_of(frm.doctype),
		stages: compras.steps.STEPS.map(([key, , label, group]) => ({
			key,
			label,
			optional: group ? 1 : 0,
			group: group || null,
			group_label: group ? compras.steps.GROUP_LABELS[group] : null,
			status: "none",
			count: 0,
			restricted: 0,
			alerts: [],
			docs: [],
		})),
	};
};

compras.steps.render = function (frm, model) {
	const esc = (value) => frappe.utils.escape_html(value == null ? "" : String(value));
	frm.$wrapper.find(".cmp-steps").remove();
	const stages = model.stages || [];
	// An optional stage nobody used (e.g. direct purchase without quotation) does not count towards progress.
	const counted = stages.filter((stage) => !(stage.optional && stage.status === "none"));
	const done = counted.filter((stage) => stage.status === "ok").length;
	const current = stages.find((stage) => stage.key === model.current);
	const collapsed = compras.steps.is_collapsed();

	const items = stages
		.map((stage, index) => {
			const is_current = stage.key === model.current;
			const status_text = compras.steps.STATUS_TEXT[stage.status] || "";
			const visible_docs = (stage.docs || []).filter((doc) => doc.name);
			const clickable = !is_current && visible_docs.length > 0;
			const alerts = (stage.alerts || []).map((alert) => `<li>${esc(alert)}</li>`).join("");
			const doc_rows = visible_docs
				.slice(0, 5)
				.map(
					(doc) => `<li><b>${esc(doc.name)}</b>${doc.title ? ` — ${esc(doc.title)}` : ""}
						<span class="cmp-tip-doc-status">${esc(__(doc.doctype))} · ${esc(
						doc.status_label || ""
					)}</span></li>`
				)
				.join("");
			const more =
				visible_docs.length > 5
					? `<li>${__("+ {0} outros", [visible_docs.length - 5])}</li>`
					: "";
			const hidden = stage.restricted
				? `<li>${__("{0} sem permissão de leitura", [stage.restricted])}</li>`
				: "";
			const optional = stage.optional ? ` <i>(${__("opcional")})</i>` : "";
			const tip = `<div class="cmp-tip"><div class="cmp-tip-title">${esc(
				stage.label
			)}${optional}</div>
				<div class="cmp-tip-status is-${esc(stage.status)}">${esc(status_text)}</div>
				<p class="cmp-tip-help">${esc(compras.steps.STATUS_HELP[stage.status] || "")}</p>
				${
					alerts
						? `<div class="cmp-tip-section">${__(
								"Pontos de atenção"
						  )}</div><ul class="cmp-tip-alerts">${alerts}</ul>`
						: ""
				}
				${
					doc_rows || hidden
						? `<div class="cmp-tip-section">${__(
								"Documentos"
						  )}</div><ul class="cmp-tip-docs">${doc_rows}${more}${hidden}</ul>`
						: ""
				}
				${clickable ? `<div class="cmp-tip-hint">${__("Clique para abrir")}</div>` : ""}</div>`;
			const marker =
				stage.status === "ok" ? "&#10003;" : stage.status === "warn" ? "!" : index + 1;
			const count =
				stage.count > 1 ? `<span class="cmp-steps-count">${stage.count}</span>` : "";
			// Consecutive stages with the same group share one dashed outline (start / middle / end pieces).
			const group = stage.group;
			const group_start = group && stages[index - 1]?.group !== group;
			const group_end = group && stages[index + 1]?.group !== group;
			const group_class = group
				? ` in-group${group_start ? " is-group-start" : ""}${
						group_end ? " is-group-end" : ""
				  }`
				: "";
			const group_tag = group_start
				? `<span class="cmp-group-tag">${esc(
						stage.group_label || compras.steps.GROUP_LABELS[group] || ""
				  )}</span>`
				: "";
			return `<li class="cmp-step is-${esc(stage.status)}${is_current ? " is-current" : ""}${
				clickable ? " is-link" : ""
			}${group_class}"
					data-key="${esc(stage.key)}" data-tip="${esc(tip)}" ${is_current ? 'aria-current="step"' : ""}>
				${group_tag}
				<span class="cmp-step-marker">${marker}</span>
				<span class="cmp-step-text">
					<span class="cmp-step-label">${esc(stage.label)}${count}</span>
					<span class="cmp-step-status">${esc(is_current ? __("Você está aqui") : status_text)}</span>
				</span>
			</li>`;
		})
		.join("");

	const $bar = $(`
		<div class="cmp-steps${collapsed ? " is-collapsed" : ""}">
			<button type="button" class="cmp-steps-pill" aria-expanded="false">
				<span class="cmp-steps-pill-title">${__("Etapas do processo")}</span>
				<span class="cmp-steps-pill-meta">${esc(current ? current.label : "")} · ${done}/${
		counted.length
	}</span>
				<span aria-hidden="true">&#9656;</span>
			</button>
			<div class="cmp-steps-panel">
				<div class="cmp-steps-head">
					<span class="cmp-steps-title">${__("Etapas do processo")}</span>
					<span class="cmp-steps-progress">${__("{0} de {1} concluídas", [done, counted.length])}</span>
					<span class="cmp-steps-actions">
						<button type="button" class="cmp-steps-close" aria-label="${__("Recolher etapas")}" title="${__(
		"Recolher etapas"
	)}">&times;</button>
					</span>
				</div>
				<ol class="cmp-steps-track">${items}</ol>
			</div>
		</div>
	`);

	$bar.find(".cmp-steps-pill").on("click", () => {
		compras.steps.set_collapsed(false);
		$bar.removeClass("is-collapsed");
	});
	$bar.find(".cmp-steps-close").on("click", () => {
		compras.steps.set_collapsed(true);
		$bar.addClass("is-collapsed");
	});
	$bar.find(".cmp-step.is-link").on("click", function () {
		const stage = stages.find((row) => row.key === $(this).data("key"));
		compras.steps.open_stage(stage);
	});

	compras.steps.bind_tooltips($bar);
	frm.layout.wrapper.before($bar);
	// Keep the current step in view on narrow screens.
	const $current = $bar.find(".cmp-step.is-current");
	const $track = $bar.find(".cmp-steps-track");
	if ($current.length && $track[0].scrollWidth > $track[0].clientWidth) {
		$track.scrollLeft($current.position().left - 24);
	}
};

// One hover card for the whole page: a bar removed while its card is open never receives mouseleave.
compras.steps.hide_tip = function () {
	$(".cmp-tip-pop").remove();
};

compras.steps.bind_tooltips = function ($bar) {
	compras.steps.hide_tip();
	$bar.on("mouseenter focusin", ".cmp-step", function () {
		compras.steps.hide_tip();
		const $tip = $(
			`<div class="cmp-tip-pop" role="tooltip">${$(this).attr("data-tip")}</div>`
		).appendTo("body");
		const rect = this.getBoundingClientRect();
		const width = $tip.outerWidth();
		const left = Math.max(
			8,
			Math.min(window.innerWidth - width - 8, rect.left + rect.width / 2 - width / 2)
		);
		$tip.css({ left, top: rect.bottom + 8 });
	});
	$bar.on("mouseleave focusout", ".cmp-step", compras.steps.hide_tip);
	$bar.find(".cmp-steps-track").on("scroll", compras.steps.hide_tip);
	$bar.on("click", ".cmp-steps-close, .cmp-steps-pill", compras.steps.hide_tip);
};

if (!compras.steps.__tip_guard) {
	compras.steps.__tip_guard = true;
	$(document).on("mouseover", (e) => {
		if (!$(e.target).closest(".cmp-step").length) compras.steps.hide_tip();
	});
	$(document).on("page-change", compras.steps.hide_tip);
	frappe.router.on("change", compras.steps.hide_tip);
	window.addEventListener("scroll", compras.steps.hide_tip, true);
}

compras.steps.open_stage = function (stage) {
	const docs = (stage.docs || []).filter((doc) => doc.name);
	if (docs.length === 1) return frappe.set_route("Form", docs[0].doctype, docs[0].name);
	const esc = frappe.utils.escape_html;
	const rows = docs
		.map(
			(doc) => `<a class="list-group-item" href="${frappe.utils.get_form_link(
				doc.doctype,
				doc.name
			)}">
				<b>${esc(doc.name)}</b>${doc.title ? ` — ${esc(doc.title)}` : ""}
				<span class="text-muted pull-right">${esc(__(doc.doctype))} · ${esc(doc.status_label || "")}</span>
			</a>`
		)
		.join("");
	const dialog = new frappe.ui.Dialog({
		title: stage.label,
		fields: [{ fieldtype: "HTML", fieldname: "docs" }],
	});
	dialog.fields_dict.docs.$wrapper.html(`<div class="list-group">${rows}</div>`);
	dialog.$wrapper.on("click", "a", () => dialog.hide());
	dialog.show();
};

compras.steps.refresh = function (frm) {
	// Service-procurement Material Requests are handled by the CLM; only purchase requests belong here.
	if (frm.doctype === "Material Request" && frm.doc.material_request_type !== "Purchase") return;
	if (frm.is_new()) return compras.steps.render(frm, compras.steps.local_model(frm));
	const token = (frm.__cmp_steps_token = (frm.__cmp_steps_token || 0) + 1);
	frappe
		.xcall("integracoes_customizadas.compras.process_view.get_purchase_steps", {
			doctype: frm.doctype,
			name: frm.doc.name,
		})
		.then((model) => {
			// A later refresh (or another document in the same form) superseded this call.
			if (token !== frm.__cmp_steps_token || !model) return;
			compras.steps.render(frm, model);
		});
};

compras.steps.STEPS.forEach(([, doctypes]) =>
	doctypes.forEach((doctype) =>
		frappe.ui.form.on(doctype, "refresh", (frm) => compras.steps.refresh(frm))
	)
);

// Purchase Receipt: remind the unit to register the Nota Fiscal.
frappe.ui.form.on("Purchase Receipt", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || frm.doc.is_return || frm.doc.custom_compras_nf_numero)
			return;
		frm.dashboard.set_headline_alert(
			__(
				"Nota Fiscal ainda não informada. Preencha a seção «Nota Fiscal do Fornecedor» para liberar o faturamento."
			),
			"orange"
		);
	},
});
