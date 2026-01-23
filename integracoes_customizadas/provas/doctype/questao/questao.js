// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Questao", {
	disciplina: function(frm) {
		if (frm.doc.disciplina) {
			frappe.db.get_value("Disciplina", frm.doc.disciplina, "aplicavel_a_todos", (r) => {
				if (r) {
					frm.set_value("__disciplina_aplicavel_a_todos", r.aplicavel_a_todos);
					
					// Se a disciplina é aplicável a todos, limpa os cargos
					if (r.aplicavel_a_todos) {
						frm.clear_table("designations");
						frm.refresh_field("designations");
					}
				}
			});
		} else {
			frm.set_value("__disciplina_aplicavel_a_todos", 0);
		}
	},
	
	refresh: function(frm) {
		// Inicializa a variável se a disciplina já estiver preenchida
		if (frm.doc.disciplina && !frm.doc.__disciplina_aplicavel_a_todos) {
			frappe.db.get_value("Disciplina", frm.doc.disciplina, "aplicavel_a_todos", (r) => {
				if (r) {
					frm.set_value("__disciplina_aplicavel_a_todos", r.aplicavel_a_todos);
					frm.refresh_field("designations");
				}
			});
		}
	}
});
