// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Prova", {
	refresh: function(frm) {
		// Evita ações em documentos submetidos/cancelados
		if (frm.doc.docstatus && frm.doc.docstatus !== 0) {
			return;
		}

		// Adiciona botões quando edital estiver preenchido (mesmo em documento novo)
		if (frm.doc.edital) {
			frm.add_custom_button(__("Selecionar Questões"), function() {
				frm.events.abrir_dialog_questoes(frm);
			}, __("Ações"));
			
			// Adiciona botão para gerar questões automaticamente
			frm.add_custom_button(__("Gerar Questões"), function() {
				frm.events.abrir_dialog_gerador(frm);
			}, __("Ações"));
		}
	},
	
	edital: function(frm) {
		// Quando o edital é alterado, atualiza o campo designation automaticamente
		if (frm.doc.edital) {
			frappe.db.get_value("Edital", frm.doc.edital, "designation", (r) => {
				if (r && r.designation) {
					frm.set_value("designation", r.designation);
				}
			});
		} else {
			frm.set_value("designation", "");
		}
	},
	
	abrir_dialog_questoes: function(frm) {
		// Valida que o edital está preenchido
		if (!frm.doc.edital) {
			frappe.msgprint(__("Por favor, selecione um Edital antes de selecionar questões."));
			return;
		}
		
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

		dialog.show();

		let $wrapper = dialog.$wrapper;
		let $filterDisciplina = $wrapper.find("#filter_disciplina");
		let $filterTipo = $wrapper.find("#filter_tipo");
		let $questoesList = $wrapper.find("#questoes_list");

		// Preenche disciplinas no filtro
		let disciplinas = [...new Set(questoes.map(q => q.disciplina))];
		disciplinas.forEach(disc => {
			$filterDisciplina.append(`<option value="${disc}">${disc}</option>`);
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
			$questoesList.html(html);
		}

		// Renderiza questões iniciais
		renderizar_questoes(questoes);

		// Filtros
		$wrapper.on("change", "#filter_disciplina, #filter_tipo", function() {
			let disciplina = $filterDisciplina.val();
			let tipo = $filterTipo.val();

			let filtradas = questoes.filter(q => {
				return (!disciplina || q.disciplina === disciplina) &&
					   (!tipo || q.tipo === tipo);
			});

			renderizar_questoes(filtradas);
		});
	},
	
	adicionar_questoes: function(frm, questoes_selecionadas) {
		// Obtém a próxima ordem
		let proxima_ordem = 1;
		if (frm.doc.questoes && frm.doc.questoes.length > 0) {
			proxima_ordem = Math.max(...frm.doc.questoes.map(q => q.ordem || 0)) + 1;
		}
		
		let questoes_existentes = new Set();
		if (frm.doc.questoes && frm.doc.questoes.length > 0) {
			frm.doc.questoes.forEach(q => {
				if (q.questao) {
					questoes_existentes.add(q.questao);
				}
			});
		}
		
		let questoes_filtradas = [];
		let questoes_adicionadas = new Set();
		(questoes_selecionadas || []).forEach(questao_name => {
			if (!questao_name) {
				return;
			}
			if (questoes_existentes.has(questao_name)) {
				return;
			}
			if (questoes_adicionadas.has(questao_name)) {
				return;
			}
			questoes_adicionadas.add(questao_name);
			questoes_filtradas.push(questao_name);
		});
		
		// Adiciona questões à tabela
		questoes_filtradas.forEach((questao_name, index) => {
			let row = frm.add_child("questoes");
			row.questao = questao_name;
			row.ordem = proxima_ordem + index;
			row.peso = 1.0; // Peso padrão
		});
		
		frm.refresh_field("questoes");
		frappe.show_alert({
			message: __("{0} questão(ões) adicionada(s)", [questoes_filtradas.length]),
			indicator: "green"
		}, 3);
	},
	
	abrir_dialog_gerador: function(frm) {
		// Valida que o edital está preenchido
		if (!frm.doc.edital) {
			frappe.msgprint(__("Por favor, selecione um Edital antes de gerar questões."));
			return;
		}
		
		// Valida que o cargo está preenchido (vem do edital)
		if (!frm.doc.designation) {
			frappe.msgprint(__("O Edital selecionado não possui cargo definido."));
			return;
		}
		
		// Cria dialog com tabela dinâmica
		let dialog = new frappe.ui.Dialog({
			title: __("Gerador Automático de Questões"),
			fields: [
				{
					fieldtype: "HTML",
					options: `
						<div class="alert alert-info">
							<p><strong>Instruções:</strong></p>
							<p>Configure as disciplinas e a quantidade de questões desejada para cada uma. 
							O sistema selecionará questões aleatórias aplicáveis ao cargo <strong>${frm.doc.designation}</strong>.</p>
							<p><small>Edital: ${frm.doc.edital}</small></p>
						</div>
					`
				},
				{
					fieldname: "configuracoes",
					fieldtype: "Table",
					label: __("Configurações de Disciplinas"),
					fields: [
						{
							fieldname: "disciplina",
							fieldtype: "Link",
							options: "Disciplina",
							label: __("Disciplina"),
							reqd: 1,
							in_list_view: 1
						},
						{
							fieldname: "quantidade",
							fieldtype: "Int",
							label: __("Quantidade"),
							reqd: 1,
							default: 1,
							in_list_view: 1
						},
						{
							fieldname: "dificuldade",
							fieldtype: "Select",
							label: __("Dificuldade"),
							options: "Aleatória\nFácil\nMédia\nDifícil",
							default: "Aleatória",
							in_list_view: 1
						}
					],
					reqd: 1
				}
			],
			primary_action_label: __("Gerar Questões"),
			primary_action: function() {
				let configuracoes = dialog.get_value("configuracoes");
				
				if (!configuracoes || configuracoes.length === 0) {
					frappe.msgprint(__("Por favor, adicione pelo menos uma disciplina."));
					return;
				}
				
				// Valida configurações
				for (let config of configuracoes) {
					if (!config.disciplina) {
						frappe.msgprint(__("Todas as disciplinas devem ser preenchidas."));
						return;
					}
					if (!config.quantidade || config.quantidade < 1) {
						frappe.msgprint(__("A quantidade deve ser pelo menos 1 para cada disciplina."));
						return;
					}
				}
				
				frm.events.gerar_questoes_automaticas(frm, configuracoes);
				dialog.hide();
			}
		});
		
		dialog.show();
	},
	
	gerar_questoes_automaticas: function(frm, configuracoes) {
		let questoes_existentes = [];
		if (frm.doc.questoes && frm.doc.questoes.length > 0) {
			questoes_existentes = frm.doc.questoes.map(q => q.questao);
		}

		frappe.call({
			method: "integracoes_customizadas.provas.doctype.prova.prova.gerar_questoes_automaticas",
			args: {
				designation: frm.doc.designation,
				configuracoes: configuracoes,
				questoes_excluir: questoes_existentes
			},
			freeze: true,
			freeze_message: __("Gerando questões..."),
			callback: function(r) {
				if (r.message) {
					let resultado = r.message;
					
					// Adiciona questões à tabela
					if (resultado.questoes_selecionadas && resultado.questoes_selecionadas.length > 0) {
						frm.events.adicionar_questoes(frm, resultado.questoes_selecionadas);
					}
					
					// Mostra resumo
					let mensagem = __("{0} questão(ões) adicionada(s)", [resultado.total_adicionadas]);
					if (resultado.avisos && resultado.avisos.length > 0) {
						mensagem += "\n\n" + __("Avisos:") + "\n" + resultado.avisos.join("\n");
						frappe.msgprint(mensagem, indicator="orange", title=__("Geração Concluída"));
					} else {
						frappe.msgprint(mensagem, indicator="green", title=__("Sucesso"));
					}
				}
			}
		});
	}
});
