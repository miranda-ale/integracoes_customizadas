// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Prova", {
	refresh: function(frm) {
		// Adiciona botão para selecionar questões
		if (!frm.is_new()) {
			frm.add_custom_button(__("Selecionar Questões"), function() {
				frm.events.abrir_dialog_questoes(frm);
			}, __("Ações"));
		}
	},
	
	abrir_dialog_questoes: function(frm) {
		// Busca questões disponíveis
		frappe.call({
			method: "integracoes_customizadas.provas.doctype.prova.prova.get_questoes_disponiveis",
			args: {
				prova_name: frm.doc.name,
				designation: frm.doc.designation,
				disciplina: null,
				tipo: null
			},
			callback: function(r) {
				if (r.message) {
					frm.events.mostrar_dialog_questoes(frm, r.message);
				}
			}
		});
	},
	
	mostrar_dialog_questoes: function(frm, questoes) {
		let dialog = new frappe.ui.Dialog({
			title: __("Selecionar Questões"),
			fields: [
				{
					fieldtype: "HTML",
					options: `
						<div style="margin-bottom: 15px;">
							<div class="row">
								<div class="col-sm-6">
									<label class="control-label">Filtrar por Disciplina</label>
									<select class="form-control" id="filter_disciplina" style="margin-bottom: 10px;">
										<option value="">Todas</option>
									</select>
								</div>
								<div class="col-sm-6">
									<label class="control-label">Filtrar por Tipo</label>
									<select class="form-control" id="filter_tipo" style="margin-bottom: 10px;">
										<option value="">Todos</option>
										<option value="Objetiva">Objetiva</option>
										<option value="Discursiva">Discursiva</option>
									</select>
								</div>
							</div>
						</div>
						<div id="questoes_list" style="max-height: 500px; overflow-y: auto;">
							<!-- Questões serão inseridas aqui -->
						</div>
					`
				}
			],
			primary_action_label: __("Adicionar Selecionadas"),
			primary_action: function() {
				let selecionadas = [];
				$("#questoes_list input[type='checkbox']:checked").each(function() {
					selecionadas.push($(this).data("questao"));
				});
				
				if (selecionadas.length === 0) {
					frappe.msgprint(__("Por favor, selecione pelo menos uma questão."));
					return;
				}
				
				frm.events.adicionar_questoes(frm, selecionadas);
				dialog.hide();
			}
		});
		
		// Preenche disciplinas no filtro
		let disciplinas = [...new Set(questoes.map(q => q.disciplina))];
		disciplinas.forEach(disc => {
			$("#filter_disciplina").append(`<option value="${disc}">${disc}</option>`);
		});
		
		// Função para renderizar questões
		function renderizar_questoes(lista_questoes) {
			let html = "";
			if (lista_questoes.length === 0) {
				html = "<p class='text-muted'>Nenhuma questão encontrada.</p>";
			} else {
				lista_questoes.forEach(questao => {
					html += `
						<div class="panel panel-default" style="margin-bottom: 10px;">
							<div class="panel-body">
								<div class="row">
									<div class="col-sm-1">
										<input type="checkbox" data-questao="${questao.name}" style="margin-top: 5px;">
									</div>
									<div class="col-sm-11">
										<h5 style="margin-top: 0;">
											${questao.name} - ${questao.tipo} 
											<span class="label label-default">${questao.disciplina}</span>
											<span class="label label-info">${questao.dificuldade}</span>
										</h5>
										<div style="max-height: 100px; overflow-y: auto; margin-top: 10px;">
											${questao.enunciado || ""}
										</div>
									</div>
								</div>
							</div>
						</div>
					`;
				});
			}
			$("#questoes_list").html(html);
		}
		
		// Renderiza questões iniciais
		renderizar_questoes(questoes);
		
		// Filtros
		$("#filter_disciplina, #filter_tipo").on("change", function() {
			let disciplina = $("#filter_disciplina").val();
			let tipo = $("#filter_tipo").val();
			
			let filtradas = questoes.filter(q => {
				return (!disciplina || q.disciplina === disciplina) &&
					   (!tipo || q.tipo === tipo);
			});
			
			renderizar_questoes(filtradas);
		});
		
		dialog.show();
	},
	
	adicionar_questoes: function(frm, questoes_selecionadas) {
		// Obtém a próxima ordem
		let proxima_ordem = 1;
		if (frm.doc.questoes && frm.doc.questoes.length > 0) {
			proxima_ordem = Math.max(...frm.doc.questoes.map(q => q.ordem || 0)) + 1;
		}
		
		// Adiciona questões à tabela
		questoes_selecionadas.forEach((questao_name, index) => {
			let row = frm.add_child("questoes");
			row.questao = questao_name;
			row.ordem = proxima_ordem + index;
			row.peso = 1.0; // Peso padrão
		});
		
		frm.refresh_field("questoes");
		frappe.show_alert({
			message: __("{0} questão(ões) adicionada(s)", [questoes_selecionadas.length]),
			indicator: "green"
		}, 3);
	}
});
