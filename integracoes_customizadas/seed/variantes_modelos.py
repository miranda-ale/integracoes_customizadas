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
	"Boas-vindas": [
		'Oi, {{ seguro(doc.employee_name) }}! 👋 Seja muito bem-vindo(a) à *BHCL*!\n\n*Cargo:* {{ seguro(doc.designation) }}\n*Unidade:* {{ seguro(doc.company) }}{% if doc.department %} ({{ seguro(doc.department) }}){% endif %}\n*Início:* {{ data(doc.date_of_joining) or "-" }}\n\nQualquer dúvida, fale com o RH. Boa jornada!',
		'Olá, {{ seguro(doc.employee_name) }}! Que alegria ter você no time 🙌\n\n*Cargo:* {{ seguro(doc.designation) }}\n*Unidade:* {{ seguro(doc.company) }}{% if doc.department %} ({{ seguro(doc.department) }}){% endif %}\n*Início:* {{ data(doc.date_of_joining) or "-" }}\n\nO RH está à disposição pra o que precisar.',
		'{{ seguro(doc.employee_name) }}, bem-vindo(a) à *Beneficência Hospitalar de Cesário Lange* 💙\n\n*Cargo:* {{ seguro(doc.designation) }}\n*Unidade:* {{ seguro(doc.company) }}{% if doc.department %} ({{ seguro(doc.department) }}){% endif %}\n*Início:* {{ data(doc.date_of_joining) or "-" }}\n\nConta com a gente, e em caso de dúvida procure o RH.',
		'Oi, {{ seguro(doc.employee_name) }}! Chegou o grande dia 🎉 Você agora faz parte da *BHCL*.\n\n*Cargo:* {{ seguro(doc.designation) }}\n*Unidade:* {{ seguro(doc.company) }}{% if doc.department %} ({{ seguro(doc.department) }}){% endif %}\n*Início:* {{ data(doc.date_of_joining) or "-" }}\n\nDúvidas? O RH te ajuda.',
		'Olá, {{ seguro(doc.employee_name) }}, tudo bem? Seja bem-vindo(a) ao time da *BHCL* 😊\n\n*Cargo:* {{ seguro(doc.designation) }}\n*Unidade:* {{ seguro(doc.company) }}{% if doc.department %} ({{ seguro(doc.department) }}){% endif %}\n*Início:* {{ data(doc.date_of_joining) or "-" }}\n\nBoa jornada e conte com o RH!',
		'Que bom ter você aqui, {{ seguro(doc.employee_name) }}! 🌟\n\n*Cargo:* {{ seguro(doc.designation) }}\n*Unidade:* {{ seguro(doc.company) }}{% if doc.department %} ({{ seguro(doc.department) }}){% endif %}\n*Início:* {{ data(doc.date_of_joining) or "-" }}\n\nSe precisar de algo, chame o Departamento de Recursos Humanos.',
		'Oi, {{ seguro(doc.employee_name) }}! Passando pra dar as boas-vindas à *BHCL* 🤝\n\n*Cargo:* {{ seguro(doc.designation) }}\n*Unidade:* {{ seguro(doc.company) }}{% if doc.department %} ({{ seguro(doc.department) }}){% endif %}\n*Início:* {{ data(doc.date_of_joining) or "-" }}\n\nFicamos felizes com a sua chegada. Qualquer dúvida, fale com o RH.',
		'Olá, {{ seguro(doc.employee_name) }}! É um prazer receber você na *BHCL* ✨\n\n*Cargo:* {{ seguro(doc.designation) }}\n*Unidade:* {{ seguro(doc.company) }}{% if doc.department %} ({{ seguro(doc.department) }}){% endif %}\n*Início:* {{ data(doc.date_of_joining) or "-" }}\n\nO RH está por perto para ajudar no que for preciso.',
		'Boas-vindas, {{ seguro(doc.employee_name) }}! 🚀 Começa agora a sua jornada na *BHCL*.\n\n*Cargo:* {{ seguro(doc.designation) }}\n*Unidade:* {{ seguro(doc.company) }}{% if doc.department %} ({{ seguro(doc.department) }}){% endif %}\n*Início:* {{ data(doc.date_of_joining) or "-" }}\n\nDúvidas? É só chamar o RH.',
		'Oi, {{ seguro(doc.employee_name) }}! Todo o time da *BHCL* deseja uma ótima chegada 🙂\n\n*Cargo:* {{ seguro(doc.designation) }}\n*Unidade:* {{ seguro(doc.company) }}{% if doc.department %} ({{ seguro(doc.department) }}){% endif %}\n*Início:* {{ data(doc.date_of_joining) or "-" }}\n\nPrecisando de algo, procure o Recursos Humanos.',
	],
	"Tarefa": [
		'Olá,\nvocê recebeu uma tarefa de integração 📝\n\n*Tarefa:* {{ seguro(doc.description) }}\n*Prazo:* {{ data(doc.date) or "-" }}\n*Prioridade:* {{ doc.priority }}\n*ID da tarefa:* {{ doc.reference_name }}\n\n{{ url() }}/app/task/{{ doc.reference_name }}',
		'Oi! Tem uma tarefa de integração nova pra você 📌\n\n*Tarefa:* {{ seguro(doc.description) }}\n*Prazo:* {{ data(doc.date) or "-" }}\n*Prioridade:* {{ doc.priority }}\n*ID da tarefa:* {{ doc.reference_name }}\n\nAcesse: {{ url() }}/app/task/{{ doc.reference_name }}',
		'Olá! Uma tarefa de integração foi atribuída a você ✅\n\n*Tarefa:* {{ seguro(doc.description) }}\n*Prazo:* {{ data(doc.date) or "-" }}\n*Prioridade:* {{ doc.priority }}\n*ID da tarefa:* {{ doc.reference_name }}\n\nVeja em {{ url() }}/app/task/{{ doc.reference_name }}',
		'Oi, tudo bem? Passando pra avisar de uma tarefa da sua integração 🗂️\n\n*Tarefa:* {{ seguro(doc.description) }}\n*Prazo:* {{ data(doc.date) or "-" }}\n*Prioridade:* {{ doc.priority }}\n*ID da tarefa:* {{ doc.reference_name }}\n\n{{ url() }}/app/task/{{ doc.reference_name }}',
		'Ei! Chegou tarefa de integração 🚀\n\n*Tarefa:* {{ seguro(doc.description) }}\n*Prazo:* {{ data(doc.date) or "-" }}\n*Prioridade:* {{ doc.priority }}\n*ID da tarefa:* {{ doc.reference_name }}\n\nÉ só abrir: {{ url() }}/app/task/{{ doc.reference_name }}',
		'Olá! Sua integração tem uma pendência nova 🔔\n\n*Tarefa:* {{ seguro(doc.description) }}\n*Prazo:* {{ data(doc.date) or "-" }}\n*Prioridade:* {{ doc.priority }}\n*ID da tarefa:* {{ doc.reference_name }}\n\nDetalhes: {{ url() }}/app/task/{{ doc.reference_name }}',
		'Oi! Dá uma olhada nessa tarefa de integração 👀\n\n*Tarefa:* {{ seguro(doc.description) }}\n*Prazo:* {{ data(doc.date) or "-" }}\n*Prioridade:* {{ doc.priority }}\n*ID da tarefa:* {{ doc.reference_name }}\n\nLink: {{ url() }}/app/task/{{ doc.reference_name }}',
		'Olá, lembrete de tarefa da integração 🕒\n\n*Tarefa:* {{ seguro(doc.description) }}\n*Prazo:* {{ data(doc.date) or "-" }}\n*Prioridade:* {{ doc.priority }}\n*ID da tarefa:* {{ doc.reference_name }}\n\nAcesse aqui: {{ url() }}/app/task/{{ doc.reference_name }}',
		'Oi! Foi criada uma tarefa pra você na integração 🙂\n\n*Tarefa:* {{ seguro(doc.description) }}\n*Prazo:* {{ data(doc.date) or "-" }}\n*Prioridade:* {{ doc.priority }}\n*ID da tarefa:* {{ doc.reference_name }}\n\nConfira: {{ url() }}/app/task/{{ doc.reference_name }}',
		'Olá! Mais uma etapa da sua integração te espera 📎\n\n*Tarefa:* {{ seguro(doc.description) }}\n*Prazo:* {{ data(doc.date) or "-" }}\n*Prioridade:* {{ doc.priority }}\n*ID da tarefa:* {{ doc.reference_name }}\n\nAbra em {{ url() }}/app/task/{{ doc.reference_name }}',
	],
}
