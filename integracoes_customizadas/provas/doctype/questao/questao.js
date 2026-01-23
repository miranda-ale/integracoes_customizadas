// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Questao", {
	disciplina: function(frm) {
		if (frm.doc.disciplina) {
			frappe.db.get_value("Disciplina", frm.doc.disciplina, "aplicavel_a_todos", (r) => {
				if (r) {
					frm.set_value("disciplina_aplicavel_a_todos", r.aplicavel_a_todos ? 1 : 0);
					
					// Se a disciplina é aplicável a todos, limpa os cargos
					if (r.aplicavel_a_todos) {
						frm.clear_table("designations");
						frm.refresh_field("designations");
					}
					
					// Atualiza a obrigatoriedade do campo designations
					frm.refresh_field("designations");
				}
			});
		} else {
			frm.set_value("disciplina_aplicavel_a_todos", 0);
			frm.refresh_field("designations");
		}
	},
	
	refresh: function(frm) {
		// Inicializa o campo se a disciplina já estiver preenchida
		if (frm.doc.disciplina) {
			if (frm.doc.disciplina_aplicavel_a_todos === undefined || frm.doc.disciplina_aplicavel_a_todos === null) {
				frappe.db.get_value("Disciplina", frm.doc.disciplina, "aplicavel_a_todos", (r) => {
					if (r) {
						frm.set_value("disciplina_aplicavel_a_todos", r.aplicavel_a_todos ? 1 : 0);
						frm.refresh_field("designations");
					}
				});
			}
		}
	}
});
