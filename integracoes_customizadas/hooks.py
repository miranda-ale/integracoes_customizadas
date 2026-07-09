app_name = "integracoes_customizadas"
app_title = "Integracoes Customizadas"
app_publisher = "Alessandro Miranda"
app_description = "Modulo de integracoes customizadas para o ERPNext"
app_email = "alessandro.siqueira@outlook.com"
app_license = "mit"

fixtures = [
    # Exporta o DocType (se estiver no filesystem / exportável)
    # DocTypes do Contencioso (Processo Judicial, CJ *, etc.) NÃO estão aqui: fonte de verdade é o filesystem (doctype/*.json); fixture não os deleta no migrate.
    {"dt": "DocType", "filters": [["name", "in", [
        "Contrato de Trabalho",
    ]]]},

    # Exporta Custom Fields relacionados
    {"dt": "Custom Field", "filters": [["dt", "in", ["Employee", "Designation", "Contrato de Trabalho"]]]},

    # Exporta Client Scripts do DocType
    {"dt": "Client Script", "filters": [["dt", "in", ["Contrato de Trabalho"]]]},

    # Exporta Print Formats do DocType (SEM duplicidade)
    {"dt": "Print Format", "filters": [["doc_type", "=", "Contrato de Trabalho"]]},

    # Exporta Property Setters (se você tiver criado/ajustado)
    {"dt": "Property Setter", "filters": [["doc_type", "=", "Contrato de Trabalho"]]},

    # Exporta Query Reports ligados ao DocType (Report do tipo "Query Report" geralmente usa ref_doctype)
    {"dt": "Report", "filters": [["ref_doctype", "=", "Contrato de Trabalho"]]},

    # Exporta Notifications do DocType
    {"dt": "Notification", "filters": [["document_type", "=", "Contrato de Trabalho"]]},

    {"dt": "Custom Field", "filters": [["name", "in", ["Interview-prova"]]]},
    {"dt": "Report", "filters": [["ref_doctype", "=", "Processo Judicial"]]},
    {"dt": "Role", "filters": [["name", "in", [
        "CJ Administrador",
        "CJ Gestor Jurídico",
        "CJ Analista Jurídico",
        "CJ Visualizador",
        "Visualizador Executivo",
        "Financeiro Contencioso",
        "RH/DP Contencioso",
    ]]]},
    {"dt": "Module Def", "filters": [["name", "in", ["Contencioso"]]]},
    {"dt": "Workflow State", "filters": [["name", "in", [
        "Rascunho", "Aberto", "Em Análise", "Em Andamento", "Sentença", "Recursos", "Execução", "Encerrado", "Arquivado",
        "A Vencer", "Vencido", "Cumprido", "Cancelado",
    ]]]},
    {"dt": "Workflow", "filters": [["name", "in", [
        "Processo Judicial",
        "CJ Prazo",
    ]]]},
    {"dt": "Workspace", "filters": [["name", "in", ["Contencioso"]]]},
    {"dt": "Number Card", "filters": [["name", "in", [
        "CJ Total Processos Ativos",
        "CJ Provisão Atual",
        "CJ Exposição Estimada",
        "CJ Prazos Próximos 7 Dias",
        "CJ Prazos Próximos 15 Dias",
        "CJ Prazos Próximos 30 Dias",
        "CJ Custos YTD",
        "CJ Audiências Futuras 30 Dias",
    ]]]},
    {"dt": "Dashboard Chart", "filters": [["name", "in", [
        "CJ Provisão por Mês",
        "CJ Processos por Status",
        "CJ Processos por Fase",
        "CJ Custos por Mês",
    ]]]},
    {"dt": "Dashboard", "filters": [["name", "in", [
        "Dashboard Executivo",
        "Dashboard Jurídico",
    ]]]},
    {"dt": "Notification", "filters": [["name", "in", [
        "Prazo Judicial D-10",
        "Prazo Judicial D-5",
        "Prazo Judicial D-1",
        "Prazo Judicial Vencido",
    ]]]},
    
]

scheduler_events = {
    "daily": [
        "integracoes_customizadas.contratos.utils.processar_alertas_contratos",
        "integracoes_customizadas.contencioso.prazos.atualizar_prazos_vencidos",
    ]
}

override_doctype_class = {
    # Corrigido: sem repetir o nome do app no import path
    "Contrato de Trabalho": "integracoes_customizadas.doctype.contrato_de_trabalho.contrato_de_trabalho.ContratoDeTrabalho"
}



# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "integracoes_customizadas",
# 		"logo": "/assets/integracoes_customizadas/logo.png",
# 		"title": "Integracoes Customizadas",
# 		"route": "/integracoes_customizadas",
# 		"has_permission": "integracoes_customizadas.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_js = "/assets/integracoes_customizadas/js/desk_theme.js"  # desativado: so servia pro experimento de topbar teal, revertido

# include js, css files in header of web template
# web_include_css = "/assets/integracoes_customizadas/css/integracoes_customizadas.css"
# web_include_js = "/assets/integracoes_customizadas/js/integracoes_customizadas.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "integracoes_customizadas/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "integracoes_customizadas/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "integracoes_customizadas.utils.jinja_methods",
# 	"filters": "integracoes_customizadas.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "integracoes_customizadas.install.before_install"
after_install = "integracoes_customizadas.provas.setup.after_install"

# Migration
# ---------
after_migrate = [
	"integracoes_customizadas.provas.setup.after_migrate",
	"integracoes_customizadas.contencioso.sync_doctype.ensure_contencioso_doctypes",
]

# Uninstallation
# ------------

# before_uninstall = "integracoes_customizadas.uninstall.before_uninstall"
# after_uninstall = "integracoes_customizadas.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "integracoes_customizadas.utils.before_app_install"
# after_app_install = "integracoes_customizadas.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "integracoes_customizadas.utils.before_app_uninstall"
# after_app_uninstall = "integracoes_customizadas.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "integracoes_customizadas.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# Processo Judicial: filtro por nivel de sigilo (contencioso)
# Buying/Stock/Selling: filtro por User Permission de Item Group (list + open)
_ITEM_GROUP_QUERY = "integracoes_customizadas.permissions.item_group_access.permission_query_conditions"
_ITEM_GROUP_PERM = "integracoes_customizadas.permissions.item_group_access.has_permission"

permission_query_conditions = {
	"Processo Judicial": "integracoes_customizadas.contencioso.permissions.processo_judicial_query_conditions",
	# Buying
	"Material Request": _ITEM_GROUP_QUERY,
	"Request for Quotation": _ITEM_GROUP_QUERY,
	"Supplier Quotation": _ITEM_GROUP_QUERY,
	"Purchase Order": _ITEM_GROUP_QUERY,
	"Purchase Receipt": _ITEM_GROUP_QUERY,
	"Purchase Invoice": _ITEM_GROUP_QUERY,
	# Selling
	"Quotation": _ITEM_GROUP_QUERY,
	"Sales Order": _ITEM_GROUP_QUERY,
	"Delivery Note": _ITEM_GROUP_QUERY,
	"Sales Invoice": _ITEM_GROUP_QUERY,
	# Stock / Manufacturing
	"Stock Entry": _ITEM_GROUP_QUERY,
	"Pick List": _ITEM_GROUP_QUERY,
	"Stock Reconciliation": _ITEM_GROUP_QUERY,
	"BOM": _ITEM_GROUP_QUERY,
	"Work Order": _ITEM_GROUP_QUERY,
	"Asset Capitalization": _ITEM_GROUP_QUERY,
}

has_permission = {
	"Processo Judicial": "integracoes_customizadas.contencioso.permissions.processo_judicial_has_permission",
	"Material Request": _ITEM_GROUP_PERM,
	"Request for Quotation": _ITEM_GROUP_PERM,
	"Supplier Quotation": _ITEM_GROUP_PERM,
	"Purchase Order": _ITEM_GROUP_PERM,
	"Purchase Receipt": _ITEM_GROUP_PERM,
	"Purchase Invoice": _ITEM_GROUP_PERM,
	"Quotation": _ITEM_GROUP_PERM,
	"Sales Order": _ITEM_GROUP_PERM,
	"Delivery Note": _ITEM_GROUP_PERM,
	"Sales Invoice": _ITEM_GROUP_PERM,
	"Stock Entry": _ITEM_GROUP_PERM,
	"Pick List": _ITEM_GROUP_PERM,
	"Stock Reconciliation": _ITEM_GROUP_PERM,
	"BOM": _ITEM_GROUP_PERM,
	"Work Order": _ITEM_GROUP_PERM,
	"Asset Capitalization": _ITEM_GROUP_PERM,
}

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"integracoes_customizadas.tasks.all"
# 	],
# 	"daily": [
# 		"integracoes_customizadas.tasks.daily"
# 	],
# 	"hourly": [
# 		"integracoes_customizadas.tasks.hourly"
# 	],
# 	"weekly": [
# 		"integracoes_customizadas.tasks.weekly"
# 	],
# 	"monthly": [
# 		"integracoes_customizadas.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "integracoes_customizadas.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "integracoes_customizadas.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "integracoes_customizadas.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "integracoes_customizadas.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["integracoes_customizadas.utils.before_request"]
# after_request = ["integracoes_customizadas.utils.after_request"]

# Job Events
# ----------
# before_job = ["integracoes_customizadas.utils.before_job"]
# after_job = ["integracoes_customizadas.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"integracoes_customizadas.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

