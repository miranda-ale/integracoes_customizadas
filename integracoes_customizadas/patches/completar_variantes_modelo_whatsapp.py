import frappe

from integracoes_customizadas.whatsapp.modelos import completar_variantes, variantes_ativas
from integracoes_customizadas.whatsapp.roteador import MIN_VARIANTES


def execute():
	"""Completa com as redações-semente os Modelos WhatsApp abaixo do mínimo de variantes (nunca sobrescreve).

	Modelo sem semente para o título continua como está e só volta a salvar com as 10 variantes: fica listado no log.
	"""
	pendentes = []
	for nome in frappe.get_all("Modelo WhatsApp", pluck="name"):
		modelo = frappe.get_doc("Modelo WhatsApp", nome)
		if completar_variantes(modelo):
			modelo.flags.ignore_validate = True  # a migração não para por um modelo de outro título
			modelo.save(ignore_permissions=True)
		if modelo.ativo and len(variantes_ativas(modelo)) < MIN_VARIANTES:
			pendentes.append(nome)
	if pendentes:
		frappe.log_error(
			"Modelos WhatsApp com menos de {0} variantes ativas: {1}".format(
				MIN_VARIANTES, ", ".join(pendentes)
			),
			"Variantes de WhatsApp pendentes",
		)
