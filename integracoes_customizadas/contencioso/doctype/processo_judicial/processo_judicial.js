/** Número CNJ: 20 dígitos — NNNNNNN-DD.AAAA.J.TR.OOOO (Resolução 65). */
function parse_cnj(value) {
	if (!value) return "";
	const digits = String(value).replace(/\D/g, "");
	return digits.slice(0, 20);
}

function format_cnj(value) {
	const digits = parse_cnj(value);
	if (digits.length === 0) return "";
	if (digits.length <= 7) return digits;
	if (digits.length <= 9) return `${digits.slice(0, 7)}-${digits.slice(7)}`;
	if (digits.length <= 13) return `${digits.slice(0, 7)}-${digits.slice(7, 9)}.${digits.slice(9)}`;
	if (digits.length <= 14) return `${digits.slice(0, 7)}-${digits.slice(7, 9)}.${digits.slice(9, 13)}.${digits.slice(13)}`;
	if (digits.length <= 16) return `${digits.slice(0, 7)}-${digits.slice(7, 9)}.${digits.slice(9, 13)}.${digits[13]}.${digits.slice(14)}`;
	return `${digits.slice(0, 7)}-${digits.slice(7, 9)}.${digits.slice(9, 13)}.${digits[13]}.${digits.slice(14, 16)}.${digits.slice(16)}`;
}

frappe.ui.form.on("Processo Judicial", {
	refresh(frm) {
		apply_party_masking(frm);
		apply_confidential_filter(frm);
		setup_cnj_field(frm);
		add_buscar_datajud_button(frm);
	},
	cj_numero_cnj(frm) {
		const raw = parse_cnj(frm.doc.cj_numero_cnj);
		if (raw.length <= 20) {
			frm.set_value("cj_numero_cnj", raw.length === 20 ? format_cnj(raw) : raw || "");
		}
	},
	cj_partes_on_form_rendered(frm) {
		apply_party_masking(frm);
	},
	cj_documentos_on_form_rendered(frm) {
		apply_confidential_filter(frm);
	},
});

function add_buscar_datajud_button(frm) {
	frm.add_custom_button(__("Buscar no Datajud"), function () {
		buscar_datajud_e_preencher(frm);
	}, __("Identificação do Processo"));
}

function buscar_datajud_e_preencher(frm) {
	const raw = parse_cnj(frm.doc.cj_numero_cnj);
	if (raw.length !== 20) {
		frappe.msgprint({
			title: __("Número CNJ inválido"),
			message: __("Informe um número CNJ com exatamente 20 dígitos para buscar no Datajud."),
			indicator: "red",
		});
		return;
	}
	frappe.call({
		method: "integracoes_customizadas.contencioso.integracoes.datajud.buscar_processo_para_form",
		args: { numero_cnj: raw },
		freeze: true,
		freeze_message: __("Buscando processo no Datajud..."),
		callback(r) {
			if (r.exc) {
				frappe.msgprint({
					title: __("Erro"),
					message: r.exc && r.exc.length ? r.exc : __("Erro ao consultar Datajud."),
					indicator: "red",
				});
				return;
			}
			const data = r.message;
			if (!data || !data.ok) {
				frappe.msgprint({
					title: __("Datajud"),
					message: (data && data.error) || __("Processo não encontrado ou integração indisponível."),
					indicator: "orange",
				});
				return;
			}
			// Preencher campos da capa (sem sobrescrever naming_series, company, responsável etc.)
			const processo = data.processo || {};
			Object.keys(processo).forEach(function (key) {
				if (frm.fields_dict[key] != null) {
					frm.set_value(key, processo[key]);
				}
			});
			// Substituir eventos de integração por idempotência: manter manuais, atualizar integração
			const eventos = data.cj_eventos || [];
			const atuais = (frm.doc.cj_eventos || []).filter(function (e) { return e.cj_origem !== "Integração"; });
			eventos.forEach(function (ev) {
				atuais.push(ev);
			});
			frm.clear_table("cj_eventos");
			atuais.forEach(function (ev) {
				const row = frm.add_child("cj_eventos");
				Object.keys(ev).forEach(function (k) { row.set(k, ev[k]); });
			});
			// Uma linha em cj_integracoes (DataJud)
			const integracoes = data.cj_integracoes || [];
			const integracoes_atuais = (frm.doc.cj_integracoes || []).filter(function (i) { return i.cj_provedor !== "DataJud"; });
			integracoes.forEach(function (i) {
				integracoes_atuais.push(i);
			});
			frm.clear_table("cj_integracoes");
			integracoes_atuais.forEach(function (i) {
				const row = frm.add_child("cj_integracoes");
				Object.keys(i).forEach(function (k) { row.set(k, i[k]); });
			});
			frm.refresh_fields(["cj_eventos", "cj_integracoes"]);
			frappe.show_alert({ message: __("Dados do Datajud preenchidos."), indicator: "green" });
		},
	});
}

function setup_cnj_field(frm) {
	const df = frm.meta.get_field("cj_numero_cnj");
	if (!df) return;
	// Display existing 20-digit value with mask when form loads
	if (frm.doc.cj_numero_cnj && parse_cnj(frm.doc.cj_numero_cnj).length === 20) {
		frm.set_value("cj_numero_cnj", format_cnj(frm.doc.cj_numero_cnj));
	}
	const input = frm.fields_dict.cj_numero_cnj?.input;
	if (!input) return;
	// Blur: normalize to 20 digits and apply mask
	input.addEventListener("blur", function () {
		const raw = parse_cnj(frm.doc.cj_numero_cnj);
		if (raw.length === 20) {
			frm.set_value("cj_numero_cnj", format_cnj(raw));
		}
	});
	// Restrict input to digits only (allow paste, then normalize on blur)
	input.addEventListener("input", function () {
		const raw = parse_cnj(this.value);
		if (raw.length <= 20) {
			this.value = raw.length === 20 ? format_cnj(raw) : raw;
		}
	});
	// Formatter for list view
	if (df.in_list_view) {
		frm.set_df_property("cj_numero_cnj", "formatter", function (value) {
			return value ? format_cnj(value) : value;
		});
	}
}

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
