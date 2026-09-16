frappe.query_reports["Relação de Processos"] = {
	filters: [
		{ fieldname: "company", label: __("Empresa"), fieldtype: "Link", options: "Company" },
		{
			fieldname: "tipo_parte", label: __("Tipo da Parte"), fieldtype: "Select",
			options: "\nEmployee\nCustomer\nSupplier",
			on_change: () => frappe.query_report.set_filter_value("parte", ""),
		},
		{
			fieldname: "parte", label: __("Parte"), fieldtype: "Dynamic Link",
			options: "tipo_parte", depends_on: "eval:doc.tipo_parte",
		},
		{
			fieldname: "fase_processo", label: __("Fase"), fieldtype: "Select",
			options: "\nPostulatória\nInstrutória\nDecisória\nRecursal\nExecução",
		},
		{
			fieldname: "status_processo", label: __("Situação"), fieldtype: "Select",
			options: "\nEm andamento\nEncerrado",
		},
		{ fieldname: "assunto", label: __("Assunto"), fieldtype: "Link", options: "Assunto Judicial" },
		{ fieldname: "tribunal", label: __("Tribunal"), fieldtype: "Data" },
		{ fieldname: "numero_processo", label: __("Número do Processo"), fieldtype: "Data" },
		{
			fieldname: "situacao_cadastro", label: __("Situação do Cadastro"), fieldtype: "Select",
			options: "\nRascunho\nCadastrado",
		},
		{ fieldname: "risco", label: __("Risco"), fieldtype: "Select", options: "\nBaixo\nMédio\nAlto" },
		{ fieldname: "grau", label: __("Grau"), fieldtype: "Data" },
		{ fieldname: "de", label: __("Ajuizado de"), fieldtype: "Date" },
		{ fieldname: "ate", label: __("Ajuizado até"), fieldtype: "Date" },
	],
	html_format: `
		<style>
			.relacao-processos .processo { break-inside: avoid; page-break-inside: avoid; margin: 0 0 15px; }
			.relacao-processos .processo h3 { font-size: 13px; margin: 0 0 6px; padding: 5px 8px; background: #f1f3f5; }
			.relacao-processos .processo table { width: 100%; border-collapse: collapse; font-size: 10px; }
			.relacao-processos .processo td { padding: 4px 7px; border: 1px solid #d9dee3; vertical-align: top; width: 50%; }
			.relacao-processos .rotulo { color: #586069; display: block; font-size: 9px; }
		</style>
		<div class="relacao-processos">
			<h2 class="text-center">{{ __(title) }}</h2>
			<p class="text-center">{{ data.length }} {{ __("processo(s)") }}</p>
			{% if subtitle %}<div>{{ subtitle }}</div>{% endif %}
			{% for row in data %}
			<div class="processo">
				<h3>{{ frappe.utils.escape_html(row.numero_processo || row.name) }}</h3>
				<table>
					<tr><td><span class="rotulo">{{ __("Empresa") }}</span>{{ frappe.utils.escape_html(row.empresa || "—") }}</td><td><span class="rotulo">{{ __("Parte") }}</span>{{ frappe.utils.escape_html(row.nome_parte || row.parte || "—") }}</td></tr>
					<tr><td><span class="rotulo">{{ __("Fase / Situação") }}</span>{{ frappe.utils.escape_html([row.fase_processo, row.status_processo].filter(Boolean).join(" / ") || "—") }}</td><td><span class="rotulo">{{ __("Tribunal / Grau") }}</span>{{ frappe.utils.escape_html([row.tribunal, row.grau].filter(Boolean).join(" / ") || "—") }}</td></tr>
					<tr><td><span class="rotulo">{{ __("Classe") }}</span>{{ frappe.utils.escape_html(row.classe_nome || "—") }}</td><td><span class="rotulo">{{ __("Órgão julgador") }}</span>{{ frappe.utils.escape_html(row.orgao_julgador_nome || "—") }}</td></tr>
					<tr><td colspan="2"><span class="rotulo">{{ __("Assuntos") }}</span>{{ frappe.utils.escape_html(row.assuntos || "—") }}</td></tr>
					<tr><td><span class="rotulo">{{ __("Ajuizamento") }}</span>{{ row.data_ajuizamento ? frappe.format(row.data_ajuizamento, {fieldtype: "Datetime"}) : "—" }}</td><td><span class="rotulo">{{ __("Risco / Valor da Causa") }}</span>{{ frappe.utils.escape_html(row.risco || "—") }} / {{ row.valor_causa != null ? frappe.format(row.valor_causa, {fieldtype: "Currency", options: "moeda"}, {moeda: row.moeda}) : "—" }}</td></tr>
					<tr><td><span class="rotulo">{{ __("Situação do Cadastro / Tipo da Parte") }}</span>{{ frappe.utils.escape_html([row.situacao_cadastro, row.tipo_parte].filter(Boolean).join(" / ") || "—") }}</td><td><span class="rotulo">{{ __("Valor da Condenação") }}</span>{{ row.valor_condenacao != null ? frappe.format(row.valor_condenacao, {fieldtype: "Currency", options: "moeda"}, {moeda: row.moeda}) : "—" }}</td></tr>
				</table>
			</div>
			{% endfor %}
		</div>
	`,
};
