// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Aplicacao Prova", {
	refresh: function(frm) {
		// Adiciona handler para o botão de vincular prova
		if (frm.doc.btn_vincular_prova) {
			frm.add_custom_button(__("Vincular Prova aos Candidatos"), function() {
				frm.events.vincular_prova(frm);
			}, __("Ações"));
		}
	},
	
	vincular_prova: function(frm) {
		if (!frm.doc.prova) {
			frappe.msgprint(__("Por favor, selecione uma prova."));
			return;
		}
		
		if (!frm.doc.candidatos || frm.doc.candidatos.length === 0) {
			frappe.msgprint(__("Por favor, adicione pelo menos um candidato."));
			return;
		}
		
		frappe.confirm(
			__("Deseja vincular a prova '{0}' aos {1} candidato(s) selecionado(s)?", [
				frm.doc.prova,
				frm.doc.candidatos.length
			]),
			function() {
				// Yes
				frappe.call({
					method: "integracoes_customizadas.provas.doctype.aplicacao_prova.aplicacao_prova.vincular_prova",
					args: {
						docname: frm.doc.name
					},
					freeze: true,
					freeze_message: __("Vinculando prova aos candidatos..."),
					callback: function(r) {
						if (r.message) {
							frm.reload_doc();
						}
					}
				});
			},
			function() {
				// No
			}
		);
	}
});
