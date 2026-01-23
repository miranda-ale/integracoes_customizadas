// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Edital", {
	refresh: function(frm) {
		// Filtro para mostrar apenas candidatos da vaga selecionada
		frm.set_query("job_applicant", "candidatos", function() {
			return {
				filters: {
					"job_title": frm.doc.job_opening
				}
			};
		});
		
		// Filtro para etapa_atual mostrar apenas etapas do edital
		if (frm.doc.etapas && frm.doc.etapas.length > 0) {
			let etapas_validas = frm.doc.etapas.map(e => e.interview_round);
			frm.set_query("etapa_atual", "candidatos", function() {
				return {
					filters: {
						"name": ["in", etapas_validas]
					}
				};
			});
		}
		
		// Adiciona botões customizados
		if (!frm.is_new()) {
			// Botão Importar Candidatos
			frm.add_custom_button(__("Importar Candidatos da Vaga"), function() {
				frm.events.importar_candidatos(frm);
			}, __("Ações"));
			
			// Botão Avançar Candidatos
			if (frm.doc.candidatos && frm.doc.candidatos.length > 0) {
				frm.add_custom_button(__("Avançar Candidatos"), function() {
					frm.events.abrir_dialog_avancar(frm);
				}, __("Ações"));
			}
			
			// Botão Gerar Blog
			if (frm.doc.descricao) {
				frm.add_custom_button(__("Gerar Publicação no Blog"), function() {
					frm.events.gerar_blog(frm);
				}, __("Ações"));
			}
		}
		
		// Mostra resumo de candidatos por etapa
		if (frm.doc.candidatos && frm.doc.candidatos.length > 0) {
			frm.events.mostrar_resumo_candidatos(frm);
		}
	},
	
	importar_candidatos: function(frm) {
		if (!frm.doc.job_opening) {
			frappe.msgprint(__("Por favor, selecione uma vaga antes de importar candidatos."));
			return;
		}
		
		frappe.confirm(
			__("Deseja importar todos os candidatos da vaga '{0}'?", [frm.doc.job_opening]),
			function() {
				frappe.call({
					method: "integracoes_customizadas.provas.doctype.edital.edital.importar_candidatos",
					args: {
						edital_name: frm.doc.name
					},
					freeze: true,
					freeze_message: __("Importando candidatos..."),
					callback: function(r) {
						if (r.message) {
							frm.reload_doc();
						}
					}
				});
			}
		);
	},
	
	abrir_dialog_avancar: function(frm) {
		// Monta lista de etapas disponíveis
		let etapas_options = frm.doc.etapas.map(e => ({
			value: e.interview_round,
			label: e.interview_round + " (Ordem: " + e.ordem + ")"
		}));
		
		// Monta lista de candidatos
		let candidatos_html = "";
		frm.doc.candidatos.forEach(c => {
			candidatos_html += `
				<div class="checkbox" style="margin-bottom: 5px;">
					<label>
						<input type="checkbox" class="candidato-checkbox" data-candidato="${c.job_applicant}">
						<strong>${c.applicant_name || c.job_applicant}</strong>
						<span class="text-muted"> - Etapa Atual: ${c.etapa_atual || "Nenhuma"}</span>
						<span class="label label-${frm.events.get_status_color(c.status_candidato)}">${c.status_candidato}</span>
					</label>
				</div>
			`;
		});
		
		let dialog = new frappe.ui.Dialog({
			title: __("Avançar Candidatos de Etapa"),
			fields: [
				{
					fieldtype: "HTML",
					options: `
						<div class="alert alert-info">
							<p>Selecione os candidatos e a próxima etapa para avançá-los no processo seletivo.</p>
						</div>
					`
				},
				{
					fieldname: "proxima_etapa",
					fieldtype: "Select",
					label: __("Próxima Etapa"),
					options: etapas_options.map(e => e.value).join("\n"),
					reqd: 1
				},
				{
					fieldname: "criar_interview",
					fieldtype: "Check",
					label: __("Criar Interview automaticamente"),
					default: 1
				},
				{
					fieldname: "enviar_email",
					fieldtype: "Check",
					label: __("Enviar email de notificação aos candidatos"),
					default: 1
				},
				{
					fieldtype: "Section Break",
					label: __("Selecione os Candidatos")
				},
				{
					fieldtype: "HTML",
					fieldname: "candidatos_html",
					options: `
						<div style="margin-bottom: 10px;">
							<button class="btn btn-xs btn-default" onclick="$('.candidato-checkbox').prop('checked', true)">
								${__("Selecionar Todos")}
							</button>
							<button class="btn btn-xs btn-default" onclick="$('.candidato-checkbox').prop('checked', false)">
								${__("Desmarcar Todos")}
							</button>
						</div>
						<div id="candidatos_list" style="max-height: 300px; overflow-y: auto; border: 1px solid #d1d8dd; padding: 10px; border-radius: 4px;">
							${candidatos_html}
						</div>
					`
				}
			],
			primary_action_label: __("Avançar Selecionados"),
			primary_action: function() {
				let proxima_etapa = dialog.get_value("proxima_etapa");
				let criar_interview = dialog.get_value("criar_interview") ? 1 : 0;
				let enviar_email = dialog.get_value("enviar_email") ? 1 : 0;
				
				let candidatos_selecionados = [];
				$(".candidato-checkbox:checked").each(function() {
					candidatos_selecionados.push($(this).data("candidato"));
				});
				
				if (candidatos_selecionados.length === 0) {
					frappe.msgprint(__("Por favor, selecione pelo menos um candidato."));
					return;
				}
				
				frappe.call({
					method: "integracoes_customizadas.provas.doctype.edital.edital.avancar_candidatos",
					args: {
						edital_name: frm.doc.name,
						candidatos: candidatos_selecionados,
						proxima_etapa: proxima_etapa,
						criar_interview: criar_interview,
						enviar_email: enviar_email
					},
					freeze: true,
					freeze_message: __("Avançando candidatos..."),
					callback: function(r) {
						if (r.message) {
							dialog.hide();
							frm.reload_doc();
						}
					}
				});
			}
		});
		
		dialog.show();
	},
	
	gerar_blog: function(frm) {
		frappe.confirm(
			__("Deseja gerar uma publicação no blog com o conteúdo deste edital?"),
			function() {
				frappe.call({
					method: "integracoes_customizadas.provas.doctype.edital.edital.gerar_blog",
					args: {
						edital_name: frm.doc.name
					},
					freeze: true,
					freeze_message: __("Gerando publicação..."),
					callback: function(r) {
						if (r.message) {
							frm.reload_doc();
						}
					}
				});
			}
		);
	},
	
	mostrar_resumo_candidatos: function(frm) {
		// Agrupa candidatos por etapa
		let resumo = {};
		frm.doc.candidatos.forEach(c => {
			let etapa = c.etapa_atual || "Sem Etapa";
			if (!resumo[etapa]) {
				resumo[etapa] = { total: 0, aprovados: 0, reprovados: 0, inscritos: 0 };
			}
			resumo[etapa].total++;
			if (c.status_candidato === "Aprovado") resumo[etapa].aprovados++;
			else if (c.status_candidato === "Reprovado") resumo[etapa].reprovados++;
			else if (c.status_candidato === "Inscrito") resumo[etapa].inscritos++;
		});
		
		// Monta HTML do resumo
		let html = `<div class="row" style="margin-top: 10px;">`;
		
		for (let etapa in resumo) {
			let dados = resumo[etapa];
			html += `
				<div class="col-sm-4" style="margin-bottom: 10px;">
					<div class="panel panel-default">
						<div class="panel-heading">
							<strong>${etapa}</strong>
						</div>
						<div class="panel-body">
							<p>Total: <strong>${dados.total}</strong></p>
							<p>Inscritos: <span class="label label-info">${dados.inscritos}</span></p>
							<p>Aprovados: <span class="label label-success">${dados.aprovados}</span></p>
							<p>Reprovados: <span class="label label-danger">${dados.reprovados}</span></p>
						</div>
					</div>
				</div>
			`;
		}
		
		html += `</div>`;
		
		// Mostra no formulário
		frm.set_df_property("section_candidatos", "description", html);
	},
	
	get_status_color: function(status) {
		switch(status) {
			case "Aprovado": return "success";
			case "Reprovado": return "danger";
			case "Eliminado": return "danger";
			case "Inscrito": return "info";
			default: return "default";
		}
	},
	
	// Handler para o botão do campo
	btn_importar_candidatos: function(frm) {
		frm.events.importar_candidatos(frm);
	},
	
	btn_avancar_candidatos: function(frm) {
		frm.events.abrir_dialog_avancar(frm);
	},
	
	btn_gerar_blog: function(frm) {
		frm.events.gerar_blog(frm);
	}
});
