frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Assuntos Judiciais"] = {
	method: "integracoes_customizadas.juridico.dashboard_chart_source.assuntos_judiciais.assuntos_judiciais.get_data",
};
