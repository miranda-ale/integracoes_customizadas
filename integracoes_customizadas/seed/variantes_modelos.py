"""Redações alternativas (tom de conversa de WhatsApp) dos Modelos WhatsApp, por título do modelo.

Semeadas uma única vez em modelos sem variantes (patch `semear_variantes_modelo_whatsapp`); depois disso são
dados editáveis do modelo e nunca são sobrescritas. Toda variante mantém as variáveis essenciais do modelo.
"""

_PAUTA = "{% if doc.pauta %}\n*Pauta:*\n{% for item in doc.pauta %}• {{ seguro(item.assunto) }}\n{% endfor %}{% endif %}"

VARIANTES = {
	"Convocação de Reunião de Comissão": [
		"Oi, {{ seguro(extra.participante.nome) }}, tudo bem? 😊\n\nPassando pra te lembrar da reunião da *{{ seguro(extra.comissao) }}*.\n\n📅 {{ data(doc.data_reuniao) }}, às {{ hora(doc.data_reuniao) }}\n📍 {{ seguro(doc.local_reuniao) or 'local a definir' }}\n"
		+ _PAUTA
		+ "\nConfirma presença pra gente, por favor?",
		"Olá, {{ seguro(extra.participante.nome) }}! A *{{ seguro(extra.comissao) }}* vai se reunir e a sua presença é importante 🙌\n\n*Quando:* {{ data(doc.data_reuniao) }} às {{ hora(doc.data_reuniao) }}\n*Onde:* {{ seguro(doc.local_reuniao) or 'a definir' }}\n"
		+ _PAUTA
		+ "\nMe avisa se consegue participar, tá?",
		"{{ seguro(extra.participante.nome) }}, tudo certo? Você foi convocado(a) pra reunião da *{{ seguro(extra.comissao) }}* 📌\n\n🗓️ {{ data(doc.data_reuniao) }} às {{ hora(doc.data_reuniao) }}\n📍 Local: {{ seguro(doc.local_reuniao) or 'a definir' }}\n"
		+ _PAUTA
		+ "\nPode confirmar se vai conseguir comparecer?",
		"E aí, {{ seguro(extra.participante.nome) }}! Tem reunião da *{{ seguro(extra.comissao) }}* marcada pra {{ data(doc.data_reuniao) }}, às {{ hora(doc.data_reuniao) }} ⏰\nO encontro vai ser em: {{ seguro(doc.local_reuniao) or 'local a definir' }}.\n"
		+ _PAUTA
		+ "\nConto com você! Só confirma aqui pra mim 👍",
		"Oi, {{ seguro(extra.participante.nome) }}! Convocação da *{{ seguro(extra.comissao) }}* 📣\n\nDia {{ data(doc.data_reuniao) }}, às {{ hora(doc.data_reuniao) }}, em {{ seguro(doc.local_reuniao) or 'local a definir' }}.\n"
		+ _PAUTA
		+ "\nVê se consegue ir e me confirma, por favor 🙂",
	],
}
