"""Redações alternativas (tom de conversa de WhatsApp) dos Modelos WhatsApp, por título do modelo.

Todo Modelo WhatsApp ativo precisa de ao menos `roteador.MIN_VARIANTES` (10) variantes ativas (ver o manifesto do clm,
seção 7a). Um modelo novo recebe ao ser criado as redações daqui que faltarem, e o patch
`completar_variantes_modelo_whatsapp` completa os existentes; depois disso são dados editáveis do modelo e nunca são
sobrescritas. Toda variante mantém as variáveis essenciais do modelo.
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
		"Bom dia, {{ seguro(extra.participante.nome) }}! Lembrete de reunião da *{{ seguro(extra.comissao) }}* 🗂️\n\n*Data:* {{ data(doc.data_reuniao) }}\n*Horário:* {{ hora(doc.data_reuniao) }}\n*Local:* {{ seguro(doc.local_reuniao) or 'a definir' }}\n"
		+ _PAUTA
		+ "\nPode me confirmar sua presença?",
		"Oi, {{ seguro(extra.participante.nome) }}! A *{{ seguro(extra.comissao) }}* marcou reunião e você está na lista de convocados ✅\n\n📅 {{ data(doc.data_reuniao) }} · ⏰ {{ hora(doc.data_reuniao) }}\n📍 {{ seguro(doc.local_reuniao) or 'local a definir' }}\n"
		+ _PAUTA
		+ "\nConsegue participar? Me responde aqui, por favor.",
		"Olá, {{ seguro(extra.participante.nome) }}, tudo bem? Estou passando pra avisar da próxima reunião da *{{ seguro(extra.comissao) }}*.\n\nVai ser no dia {{ data(doc.data_reuniao) }}, às {{ hora(doc.data_reuniao) }}, em {{ seguro(doc.local_reuniao) or 'local a definir' }} 📍\n"
		+ _PAUTA
		+ "\nSua presença faz diferença. Confirma pra gente? 🙏",
		"{{ seguro(extra.participante.nome) }}, anota aí 📝 Reunião da *{{ seguro(extra.comissao) }}*:\n\n• Dia: {{ data(doc.data_reuniao) }}\n• Hora: {{ hora(doc.data_reuniao) }}\n• Local: {{ seguro(doc.local_reuniao) or 'a definir' }}\n"
		+ _PAUTA
		+ "\nQuando puder, confirma se vai estar presente.",
		"Oi, {{ seguro(extra.participante.nome) }}! Tudo joia? A *{{ seguro(extra.comissao) }}* se reúne em {{ data(doc.data_reuniao) }}, a partir das {{ hora(doc.data_reuniao) }} 🕒\nLocal: {{ seguro(doc.local_reuniao) or 'a definir' }}.\n"
		+ _PAUTA
		+ "\nTe espero lá! Me confirma, por favor 😉",
		"Olá, {{ seguro(extra.participante.nome) }}. Segue a convocação da *{{ seguro(extra.comissao) }}* 📌\n\n🗓️ *{{ data(doc.data_reuniao) }}*, às *{{ hora(doc.data_reuniao) }}*\n📍 {{ seguro(doc.local_reuniao) or 'Local a definir' }}\n"
		+ _PAUTA
		+ "\nVocê confirma presença? Qualquer imprevisto, me avisa por aqui.",
	],
}
