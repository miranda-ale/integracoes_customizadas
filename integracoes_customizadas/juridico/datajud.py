"""Consulta e espelhamento dos metadados públicos do DataJud."""

import hashlib
import re
import secrets
import time
from collections import Counter, defaultdict, deque

import frappe
import requests
from frappe import _
from frappe.utils import add_to_date, get_datetime, now_datetime

TRIBUNAIS = (
	"stj",
	"stm",
	"tse",
	"tst",
	*(f"trf{numero}" for numero in range(1, 7)),
	"tjac",
	"tjal",
	"tjam",
	"tjap",
	"tjba",
	"tjce",
	"tjdft",
	"tjes",
	"tjgo",
	"tjma",
	"tjmg",
	"tjms",
	"tjmt",
	"tjpa",
	"tjpb",
	"tjpe",
	"tjpi",
	"tjpr",
	"tjrj",
	"tjrn",
	"tjro",
	"tjrr",
	"tjrs",
	"tjsc",
	"tjse",
	"tjsp",
	"tjto",
	*(f"trt{numero}" for numero in range(1, 25)),
	*(
		f"tre-{uf}"
		for uf in (
			"ac",
			"al",
			"am",
			"ap",
			"ba",
			"ce",
			"dft",
			"es",
			"go",
			"ma",
			"mg",
			"ms",
			"mt",
			"pa",
			"pb",
			"pe",
			"pi",
			"pr",
			"rj",
			"rn",
			"ro",
			"rr",
			"rs",
			"sc",
			"se",
			"sp",
			"to",
		)
	),
	"tjmmg",
	"tjmrs",
	"tjmsp",
)

API_BASE = "https://api-publica.datajud.cnj.jus.br"
PAGE_SIZE = 100
# A API pública chega a levar 20-35 s por consulta; o limite fica abaixo dos 120 s do gunicorn/nginx.
TIMEOUT = (10, 100)
# A sincronização em lote não pode travar um worker inteiro num tribunal fora do ar: timeout curto
# por requisição e orçamento total por execução (o resto fica para a próxima janela do cron).
TIMEOUT_LOTE = (5, 12)
ORCAMENTO_LOTE_SEGUNDOS = 20 * 60
FILA_LOTE = "datajud"
JOB_ID_LOTE = "datajud-sincronizacao-lote"

# Tipos de erro reconhecidos (mesmas opções do Select em Configurações DataJud e DataJud Sync Log).
ERRO_AUTENTICACAO = "Autenticação"
ERRO_LIMITE = "Limite de Requisições"
ERRO_NAO_ENCONTRADO = "Não Encontrado"
ERRO_INDISPONIVEL = "Indisponível"
ERRO_DADOS_INVALIDOS = "Dados Inválidos"

# Falhas seguidas do mesmo tipo que abrem o circuito; None = tipo não abre o circuito sozinho.
LIMITE_FALHAS_CIRCUITO = {
	ERRO_AUTENTICACAO: 3,
	ERRO_LIMITE: 5,
	ERRO_INDISPONIVEL: 5,
}
BACKOFF_INICIAL_MINUTOS = 15
BACKOFF_MAXIMO_MINUTOS = 240


class DataJudError(Exception):
	def __init__(self, message, *, tipo_erro=None):
		super().__init__(message)
		self.tipo_erro = tipo_erro


def _check_user():
	if frappe.session.user != "Administrator" and not {"Usuário Jurídico", "System Manager"}.intersection(
		frappe.get_roles()
	):
		frappe.throw(_("Sem permissão para acompanhar processos judiciais."), frappe.PermissionError)


@frappe.whitelist()
def listar_tribunais():
	_check_user()
	return [{"value": alias, "label": alias.upper()} for alias in TRIBUNAIS]


def _alias_do_tribunal(tribunal):
	alias = (tribunal or "").strip().lower()
	if alias.startswith("tre") and not alias.startswith("tre-"):
		alias = f"tre-{alias[3:]}"
	return alias if alias in TRIBUNAIS else None


def _numero_cnj(numero):
	if not isinstance(numero, str) or not re.fullmatch(r"[\d.\-\s]+", numero):
		frappe.throw(_("Informe um número CNJ válido."))
	normalizado = re.sub(r"\D", "", numero)
	if len(normalizado) != 20:
		frappe.throw(_("O número CNJ deve ter 20 dígitos."))
	return normalizado


def _numero_cnj_formatado(numero):
	"""Formata os 20 dígitos conforme NNNNNNN-DD.AAAA.J.TR.OOOO."""
	numero = _numero_cnj(numero)
	return f"{numero[:7]}-{numero[7:9]}.{numero[9:13]}.{numero[13]}.{numero[14:16]}.{numero[16:]}"


def _registrar_assunto(codigo, nome):
	"""Mantém o catálogo consultável usado pelas etiquetas de assuntos."""
	identificador = _id_assunto(codigo, nome)
	nome = nome or identificador
	if frappe.db.exists("Assunto Judicial", identificador):
		if frappe.db.get_value("Assunto Judicial", identificador, "nome") != nome:
			frappe.db.set_value("Assunto Judicial", identificador, "nome", nome)
	else:
		frappe.get_doc({"doctype": "Assunto Judicial", "codigo": identificador, "nome": nome}).insert(
			ignore_permissions=True
		)
	return identificador


def _chave_publica():
	chave = frappe.get_single("Configurações DataJud").get_password("api_key", raise_exception=False)
	if not chave:
		raise DataJudError(_("A chave pública do DataJud ainda não foi configurada."))
	return chave


def _mascarar_chave(chave):
	"""Nunca grava a chave completa no log: só os 4 primeiros caracteres."""
	if not chave:
		return None
	return f"{chave[:4]}…" if len(chave) > 4 else "…"


class _ColetorErros:
	"""Agrupa falhas de uma execução por tipo de erro: um registro por execução e tipo, não por processo."""

	def __init__(self):
		self.execucao = now_datetime()
		self._grupos = {}

	def registrar(self, tipo_erro, *, numero_processo=None, amostra=None):
		grupo = self._grupos.setdefault(tipo_erro, {"contagem": 0, "processos": [], "amostra": {}})
		grupo["contagem"] += 1
		if numero_processo and numero_processo not in grupo["processos"]:
			grupo["processos"].append(numero_processo)
		if amostra:
			# A ocorrência mais recente vira o exemplo gravado (endpoint, status, corpo, traceback).
			grupo["amostra"] = amostra

	@property
	def grupos(self):
		return self._grupos

	def tipo_predominante(self):
		if not self._grupos:
			return None
		return max(self._grupos, key=lambda tipo: self._grupos[tipo]["contagem"])

	def persistir(self):
		for tipo_erro, grupo in self._grupos.items():
			frappe.get_doc(
				{
					"doctype": "DataJud Sync Log",
					"execucao": self.execucao,
					"tipo_erro": tipo_erro,
					"contagem": grupo["contagem"],
					"processos_afetados": "\n".join(grupo["processos"]),
					**grupo["amostra"],
				}
			).insert(ignore_permissions=True)


def _registrar_falha(
	coletor,
	tipo_erro,
	*,
	alias,
	numero_processo,
	endpoint,
	status_http,
	tempo_resposta_ms,
	chave,
	corpo_resposta=None,
	tipo_excecao=None,
	traceback=None,
):
	amostra = {
		"tribunal": alias,
		"indice": f"api_publico_{alias}" if alias else None,
		"numero_processo": numero_processo,
		"endpoint": endpoint,
		"metodo": "POST",
		"status_http": status_http,
		"tempo_resposta_ms": tempo_resposta_ms,
		"corpo_resposta": corpo_resposta,
		"tipo_excecao": tipo_excecao,
		"traceback": traceback,
		"api_key_mascarada": _mascarar_chave(chave),
	}
	if coletor is not None:
		coletor.registrar(tipo_erro, numero_processo=numero_processo, amostra=amostra)
		return
	# Chamada interativa (sem coletor de lote): grava na hora, um registro com contagem 1.
	avulso = _ColetorErros()
	avulso.registrar(tipo_erro, numero_processo=numero_processo, amostra=amostra)
	avulso.persistir()


def _post(alias, payload, chave, *, numero_processo=None, timeout=TIMEOUT, tentativas=3, coletor=None):
	url = f"{API_BASE}/api_publica_{alias}/_search"
	for tentativa in range(tentativas):
		inicio = time.monotonic()
		try:
			resposta = requests.post(
				url,
				headers={"Authorization": f"APIKey {chave}", "Content-Type": "application/json"},
				json=payload,
				timeout=timeout,
			)
		except requests.Timeout as exc:
			tempo_ms = int((time.monotonic() - inicio) * 1000)
			_registrar_falha(
				coletor,
				ERRO_INDISPONIVEL,
				alias=alias,
				numero_processo=numero_processo,
				endpoint=url,
				status_http=None,
				tempo_resposta_ms=tempo_ms,
				tipo_excecao=type(exc).__name__,
				chave=chave,
			)
			if tentativa == tentativas - 1:
				# Repetir estouraria o limite da requisição web; a nova tentativa fica com o usuário/próxima janela.
				raise DataJudError(
					_("O DataJud demorou demais para responder. Tente novamente."),
					tipo_erro=ERRO_INDISPONIVEL,
				) from exc
		except requests.RequestException as exc:
			tempo_ms = int((time.monotonic() - inicio) * 1000)
			_registrar_falha(
				coletor,
				ERRO_INDISPONIVEL,
				alias=alias,
				numero_processo=numero_processo,
				endpoint=url,
				status_http=None,
				tempo_resposta_ms=tempo_ms,
				tipo_excecao=type(exc).__name__,
				traceback=frappe.get_traceback(),
				chave=chave,
			)
			if tentativa == tentativas - 1:
				raise DataJudError(
					_("Não foi possível conectar ao DataJud."), tipo_erro=ERRO_INDISPONIVEL
				) from exc
		else:
			tempo_ms = int((time.monotonic() - inicio) * 1000)
			if resposta.status_code in (401, 403):
				_registrar_falha(
					coletor,
					ERRO_AUTENTICACAO,
					alias=alias,
					numero_processo=numero_processo,
					endpoint=url,
					status_http=resposta.status_code,
					tempo_resposta_ms=tempo_ms,
					corpo_resposta=resposta.text[:1000],
					chave=chave,
				)
				raise DataJudError(_("Chave pública do DataJud recusada."), tipo_erro=ERRO_AUTENTICACAO)
			if resposta.status_code < 400:
				try:
					conteudo = resposta.json()
				except ValueError as exc:
					_registrar_falha(
						coletor,
						ERRO_DADOS_INVALIDOS,
						alias=alias,
						numero_processo=numero_processo,
						endpoint=url,
						status_http=resposta.status_code,
						tempo_resposta_ms=tempo_ms,
						corpo_resposta=resposta.text[:1000],
						tipo_excecao=type(exc).__name__,
						chave=chave,
					)
					raise DataJudError(
						_("Resposta JSON inválida do DataJud."), tipo_erro=ERRO_DADOS_INVALIDOS
					) from exc
				if not isinstance(conteudo, dict):
					_registrar_falha(
						coletor,
						ERRO_DADOS_INVALIDOS,
						alias=alias,
						numero_processo=numero_processo,
						endpoint=url,
						status_http=resposta.status_code,
						tempo_resposta_ms=tempo_ms,
						corpo_resposta=resposta.text[:1000],
						chave=chave,
					)
					raise DataJudError(_("Resposta inesperada do DataJud."), tipo_erro=ERRO_DADOS_INVALIDOS)
				if conteudo.get("timed_out") or (conteudo.get("_shards") or {}).get("failed", 0):
					if tentativa == tentativas - 1:
						_registrar_falha(
							coletor,
							ERRO_INDISPONIVEL,
							alias=alias,
							numero_processo=numero_processo,
							endpoint=url,
							status_http=resposta.status_code,
							tempo_resposta_ms=tempo_ms,
							corpo_resposta=resposta.text[:1000],
							chave=chave,
						)
						raise DataJudError(
							_("A pesquisa no DataJud retornou resultado incompleto."),
							tipo_erro=ERRO_INDISPONIVEL,
						)
					time.sleep(2**tentativa)
					continue
				return conteudo
			tipo_erro = (
				ERRO_LIMITE
				if resposta.status_code == 429
				else ERRO_INDISPONIVEL
				if resposta.status_code >= 500
				else ERRO_NAO_ENCONTRADO
				if resposta.status_code == 404
				else ERRO_DADOS_INVALIDOS
			)
			_registrar_falha(
				coletor,
				tipo_erro,
				alias=alias,
				numero_processo=numero_processo,
				endpoint=url,
				status_http=resposta.status_code,
				tempo_resposta_ms=tempo_ms,
				corpo_resposta=resposta.text[:1000],
				chave=chave,
			)
			if resposta.status_code != 429 and resposta.status_code < 500:
				raise DataJudError(
					_("Consulta DataJud falhou (HTTP {0}).").format(resposta.status_code), tipo_erro=tipo_erro
				)
			if tentativa == tentativas - 1:
				raise DataJudError(
					_("DataJud indisponível (HTTP {0}).").format(resposta.status_code), tipo_erro=tipo_erro
				)
		time.sleep(2**tentativa)
	raise DataJudError(_("Consulta DataJud não concluída."), tipo_erro=ERRO_INDISPONIVEL)


def consultar_numero(numero, alias, chave=None, *, timeout=TIMEOUT, tentativas=3, coletor=None):
	"""Retorna todas as ocorrências exatas, inclusive além da primeira página."""
	if alias not in TRIBUNAIS:
		frappe.throw(_("Tribunal não consta na lista de endpoints do DataJud."))
	numero = _numero_cnj(numero)
	chave = chave or _chave_publica()
	resultados = []
	identificadores = set()
	ultimo_cursor = None
	while True:
		consulta = {
			"size": PAGE_SIZE,
			"query": {"match": {"numeroProcesso": numero}},
			"sort": [{"@timestamp": {"order": "asc"}}],
		}
		if ultimo_cursor is not None:
			consulta["search_after"] = ultimo_cursor
		resposta = _post(
			alias,
			consulta,
			chave,
			numero_processo=numero,
			timeout=timeout,
			tentativas=tentativas,
			coletor=coletor,
		)
		if resposta.get("timed_out") or resposta.get("_shards", {}).get("failed", 0):
			raise DataJudError(
				_("A pesquisa no DataJud retornou resultado incompleto."), tipo_erro=ERRO_INDISPONIVEL
			)
		try:
			pagina = resposta["hits"]["hits"]
			if not isinstance(pagina, list):
				raise TypeError
		except (KeyError, TypeError) as exc:
			raise DataJudError(_("Resposta inesperada do DataJud."), tipo_erro=ERRO_DADOS_INVALIDOS) from exc
		for hit in pagina:
			fonte = hit.get("_source") or {}
			if fonte.get("numeroProcesso") == numero and _alias_do_tribunal(fonte.get("tribunal")) == alias:
				identificador = fonte.get("id") or hit.get("_id")
				if not isinstance(identificador, str) or not identificador:
					raise DataJudError(
						_("Ocorrência sem ID na resposta do DataJud."), tipo_erro=ERRO_DADOS_INVALIDOS
					)
				if identificador not in identificadores:
					resultados.append((identificador, fonte))
					identificadores.add(identificador)
		if len(pagina) < PAGE_SIZE:
			break
		cursor = pagina[-1].get("sort")
		if not cursor or cursor == ultimo_cursor:
			raise DataJudError(
				_("Paginação inválida na resposta do DataJud."), tipo_erro=ERRO_DADOS_INVALIDOS
			)
		ultimo_cursor = cursor
	return resultados


def _preencher_ocorrencia(doc, identificador, fonte, *, registrar_assuntos=True):
	doc.update(
		{
			"datajud_id": identificador,
			"numero_processo": _numero_cnj_formatado(fonte.get("numeroProcesso")),
			"tribunal": fonte.get("tribunal"),
			"grau": fonte.get("grau"),
			"nivel_sigilo": fonte.get("nivelSigilo"),
			"data_ajuizamento_original": fonte.get("dataAjuizamento"),
			"data_hora_ultima_atualizacao_original": fonte.get("dataHoraUltimaAtualizacao"),
			"timestamp_original": fonte.get("@timestamp"),
		}
	)
	for origem, prefixo in (("classe", "classe"), ("sistema", "sistema"), ("formato", "formato")):
		valor = fonte.get(origem) or {}
		doc.set(f"{prefixo}_codigo", valor.get("codigo"))
		doc.set(f"{prefixo}_nome", valor.get("nome"))
	orgao = fonte.get("orgaoJulgador") or {}
	doc.orgao_julgador_codigo = orgao.get("codigo")
	doc.orgao_julgador_nome = orgao.get("nome")
	doc.orgao_julgador_codigo_municipio_ibge = orgao.get("codigoMunicipioIBGE")
	doc.set("assuntos", [])
	for assunto in fonte.get("assuntos") or []:
		doc.append(
			"assuntos",
			{
				"assunto": (
					_registrar_assunto(assunto.get("codigo"), assunto.get("nome"))
					if registrar_assuntos
					else _id_assunto(assunto.get("codigo"), assunto.get("nome"))
				),
				"codigo": assunto.get("codigo"),
				"nome": assunto.get("nome"),
			},
		)
	anteriores = defaultdict(deque)
	for linha in doc.get("movimentos") or []:
		anteriores[_chave_movimento(linha)].append(linha)
	doc.set("movimentos", [])
	for movimento in _iterar_movimentos(fonte.get("movimentos") or []):
		orgao_movimento = movimento.get("orgaoJulgador") or {}
		valores = {
			"codigo": movimento.get("codigo"),
			"nome": movimento.get("nome"),
			"descricao": _descricao_movimento(movimento),
			"data_hora_original": movimento.get("dataHora"),
			"orgao_julgador_codigo": orgao_movimento.get("codigoOrgao", orgao_movimento.get("codigo")),
			"orgao_julgador_nome": orgao_movimento.get("nomeOrgao", orgao_movimento.get("nome")),
			"complementos_tabelados": movimento.get("complementosTabelados") or [],
		}
		chave = _chave_movimento(valores)
		if anteriores[chave]:
			linha = anteriores[chave].popleft()
			linha.update(valores)
			doc.append("movimentos", linha)
		else:
			doc.append("movimentos", valores)
	doc._atualizar_dados_datajud()
	return doc


def _iterar_movimentos(movimentos):
	"""Percorre movimentos e submovimentos na ordem recebida."""
	for movimento in movimentos:
		if not isinstance(movimento, dict):
			continue
		yield movimento
		for campo in ("movimentos", "submovimentos"):
			if isinstance(movimento.get(campo), list):
				yield from _iterar_movimentos(movimento[campo])


def _descricao_movimento(movimento):
	nome = (movimento.get("nome") or "").strip()
	complementos = movimento.get("complementosTabelados") or []
	if not isinstance(complementos, list):
		return nome
	if nome.lower().startswith("de ") and any(
		isinstance(item, dict) and item.get("descricao") == "situacao_da_audiencia" for item in complementos
	):
		nome = f"Audiência {nome}"
	partes = [nome] if nome else []
	for item in complementos:
		if not isinstance(item, dict) or not item.get("nome"):
			continue
		descricao = (item.get("descricao") or "").strip()
		valor = str(item["nome"]).strip()
		if descricao.startswith("tipo_de_distribuicao"):
			partes.append(f"por {valor}")
		elif descricao == "situacao_da_audiencia":
			partes.append(valor.capitalize())
		elif descricao == "dirigida_por":
			# O responsável pela audiência não compõe o título do andamento.
			continue
		else:
			rotulo = descricao.replace("_", " ") if descricao else "Complemento"
			partes.append(f"{rotulo}: {valor}")
	return " ".join(partes)


def _chave_movimento(movimento):
	complementos = movimento.get("complementos_tabelados") or []
	if isinstance(complementos, str):
		try:
			complementos = frappe.parse_json(complementos)
		except (ValueError, TypeError):
			pass
	return (
		movimento.get("codigo"),
		movimento.get("nome"),
		movimento.get("data_hora_original"),
		str(movimento.get("orgao_julgador_codigo")),
		movimento.get("orgao_julgador_nome"),
		frappe.as_json(complementos),
	)


def _id_assunto(codigo, nome):
	return (
		str(codigo)
		if codigo is not None and codigo != ""
		else ("nome-" + hashlib.sha1((nome or "").encode()).hexdigest()[:16])
	)


def _espelhar_ocorrencia(identificador, fonte):
	nome = frappe.db.exists("Processo Judicial", {"datajud_id": identificador})
	doc = frappe.get_doc("Processo Judicial", nome) if nome else frappe.new_doc("Processo Judicial")
	_preencher_ocorrencia(doc, identificador, fonte)
	doc.flags.from_datajud = True
	if nome:
		doc.save(ignore_permissions=True)
	else:
		doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist(methods=["POST"])
def acompanhar_processo(numero_processo, tribunal_alias):
	_check_user()
	numero = _numero_cnj(numero_processo)
	ocorrencias = consultar_numero(numero, tribunal_alias)
	resultados = []
	for identificador, fonte in ocorrencias:
		existente = frappe.db.exists("Processo Judicial", {"datajud_id": identificador})
		if existente:
			resultados.append({"name": existente, "existente": True})
			continue
		token = secrets.token_urlsafe(32)
		frappe.cache.set_value(
			f"datajud-rascunho:{token}",
			{"usuario": frappe.session.user, "fonte": fonte, "identificador": identificador},
			expires_in_sec=24 * 60 * 60,
		)
		doc = _preencher_ocorrencia(
			frappe.new_doc("Processo Judicial"), identificador, fonte, registrar_assuntos=False
		)
		doc.consulta_token = token
		resultados.append({"doc": doc.as_dict(), "existente": False})
	return resultados


def _assinaturas_movimentos(doc):
	return Counter(
		(
			movimento.codigo,
			movimento.nome,
			movimento.data_hora_original,
			movimento.orgao_julgador_codigo,
			movimento.orgao_julgador_nome,
			movimento.complementos_tabelados,
		)
		for movimento in doc.movimentos
	)


@frappe.whitelist(methods=["POST"])
def buscar_andamentos(processo):
	"""Consulta e atualiza somente a ocorrência aberta, mesmo se estiver encerrada."""
	_check_user()
	doc = frappe.get_doc("Processo Judicial", processo)
	doc.check_permission("write")
	alias = _alias_do_tribunal(doc.tribunal)
	if not alias:
		frappe.throw(_("Tribunal não consta na lista de endpoints do DataJud."))
	ocorrencias = consultar_numero(doc.numero_processo, alias)
	fonte = next((fonte for identificador, fonte in ocorrencias if identificador == doc.datajud_id), None)
	if fonte is None:
		frappe.throw(_("A ocorrência deste processo não foi encontrada no DataJud."))
	anteriores = _assinaturas_movimentos(doc)
	_espelhar_ocorrencia(doc.datajud_id, fonte)
	atualizado = frappe.get_doc("Processo Judicial", processo)
	novos = sum((_assinaturas_movimentos(atualizado) - anteriores).values())
	return {"novos_andamentos": novos, "total_andamentos": len(atualizado.movimentos)}


def _ids_em_andamento(numero, alias):
	"""Identifica as ocorrências ainda acompanhadas desse número e tribunal."""
	processos = frappe.get_all(
		"Processo Judicial",
		filters={"numero_processo": _numero_cnj_formatado(numero), "status_processo": "Em andamento"},
		fields=["datajud_id", "tribunal"],
	)
	return {p.datajud_id for p in processos if _alias_do_tribunal(p.tribunal) == alias}


def atualizar_um_processo(numero, alias, *, chave=None, timeout=TIMEOUT, tentativas=3, coletor=None):
	"""Atualiza ocorrências acompanhadas; preserva dados anteriores em caso de falha.

	Retorna True em sucesso (inclusive quando não há nada a fazer) e False quando a consulta ao
	DataJud falhou — a falha já foi classificada e registrada por `_post` (direto, se avulsa, ou no
	`coletor` da execução em lote); aqui não se grava mais um Error Log por processo.
	"""
	if not _ids_em_andamento(numero, alias):
		return True
	frappe.db.savepoint("datajud_consulta")
	try:
		for identificador, fonte in consultar_numero(
			numero, alias, chave=chave, timeout=timeout, tentativas=tentativas, coletor=coletor
		):
			ativos = _ids_em_andamento(numero, alias)
			if not ativos:
				break
			existente = frappe.db.exists("Processo Judicial", {"datajud_id": identificador})
			if existente and identificador not in ativos:
				continue
			_espelhar_ocorrencia(identificador, fonte)
		return True
	except DataJudError:
		frappe.db.rollback(save_point="datajud_consulta")
		return False
	except Exception:
		frappe.db.rollback(save_point="datajud_consulta")
		frappe.log_error(title="Falha inesperada na atualização DataJud")
		return False


def _verificar_saude(chave, coletor):
	"""Consulta mínima (size=1) num índice estável antes de processar o lote."""
	try:
		_post(
			TRIBUNAIS[0],
			{"size": 1, "query": {"match_all": {}}},
			chave,
			timeout=TIMEOUT_LOTE,
			tentativas=1,
			coletor=coletor,
		)
	except DataJudError as exc:
		return False, exc.tipo_erro or ERRO_INDISPONIVEL
	return True, None


def _circuito_permite_execucao(config):
	if not config.circuito_aberto:
		return True
	if config.circuito_tipo_falha == ERRO_AUTENTICACAO:
		# Só a troca da chave reabre (ver ConfiguraçõesDataJud.validate); não insiste sozinho.
		return False
	proxima = config.circuito_proxima_tentativa
	return bool(proxima) and now_datetime() >= get_datetime(proxima)


def _notificar_administradores(assunto, mensagem):
	try:
		from frappe.core.doctype.user.user import get_system_managers

		destinatarios = get_system_managers(only_name=False)
	except Exception:
		destinatarios = []
	if not destinatarios:
		return
	frappe.sendmail(recipients=destinatarios, subject=assunto, message=mensagem, now=False)


def _abrir_ou_manter_circuito(config, tipo_erro, *, status_http=None, mensagem=None):
	if config.circuito_tipo_falha != tipo_erro:
		config.falhas_consecutivas = 0
	config.falhas_consecutivas = (config.falhas_consecutivas or 0) + 1
	config.ultimo_erro = mensagem or tipo_erro
	config.ultimo_erro_status_http = status_http
	limite = LIMITE_FALHAS_CIRCUITO.get(tipo_erro)
	if not limite or config.falhas_consecutivas < limite:
		return
	ja_estava_aberto = bool(config.circuito_aberto)
	config.circuito_aberto = 1
	config.circuito_tipo_falha = tipo_erro
	if tipo_erro == ERRO_AUTENTICACAO:
		config.circuito_nivel_backoff = 0
		config.circuito_proxima_tentativa = None
		config.circuito_motivo = _(
			"Chave pública do DataJud recusada {0} vezes seguidas. Pausado até a troca da chave."
		).format(config.falhas_consecutivas)
	else:
		config.circuito_nivel_backoff = (config.circuito_nivel_backoff or 0) + 1 if ja_estava_aberto else 1
		minutos = min(
			BACKOFF_INICIAL_MINUTOS * (2 ** (config.circuito_nivel_backoff - 1)), BACKOFF_MAXIMO_MINUTOS
		)
		config.circuito_proxima_tentativa = add_to_date(now_datetime(), minutes=minutos)
		config.circuito_motivo = _(
			"{0} falhas seguidas de {1}. Pausado; nova tentativa automática em {2} min."
		).format(config.falhas_consecutivas, tipo_erro, minutos)
	if not ja_estava_aberto:
		config.circuito_aberto_em = now_datetime()
		_notificar_administradores(
			_("DataJud pausado automaticamente"),
			_("A sincronização com o DataJud foi pausada: {0}").format(config.circuito_motivo),
		)


def _fechar_circuito_se_necessario(config):
	estava_aberto = bool(config.circuito_aberto)
	config.circuito_aberto = 0
	config.circuito_tipo_falha = None
	config.circuito_motivo = None
	config.circuito_aberto_em = None
	config.circuito_nivel_backoff = 0
	config.circuito_proxima_tentativa = None
	config.falhas_consecutivas = 0
	config.ultimo_erro = None
	config.ultimo_erro_status_http = None
	if estava_aberto:
		_notificar_administradores(
			_("DataJud voltou ao normal"), _("A sincronização com o DataJud voltou a funcionar normalmente.")
		)


def agendar_sincronizacao():
	"""Cron (seg-sex 3h): enfileira uma única tarefa em lote, numa fila dedicada, com dedup.

	Nunca enfileira uma tarefa por processo: isso é o que fazia a fila "long" acumular dezenas de
	tarefas DataJud e atrasar tarefas interativas (como o dossiê do colaborador) na mesma fila.
	"""
	frappe.enqueue(
		"integracoes_customizadas.juridico.datajud.sincronizar_processos_acompanhados",
		queue=FILA_LOTE,
		timeout=ORCAMENTO_LOTE_SEGUNDOS + 300,
		job_id=JOB_ID_LOTE,
		deduplicate=True,
		enqueue_after_commit=True,
	)


def sincronizar_processos_acompanhados():
	"""Tarefa única por execução: health check, circuit breaker e sincronização em lote.

	Roda na fila dedicada `datajud` (ver `agendar_sincronizacao`; um worker próprio precisa escutar
	essa fila na bench — ver docs/datajud-qualidade-de-logs.md), nunca na fila "long" usada por
	tarefas interativas.
	"""
	config = frappe.get_single("Configurações DataJud")
	try:
		chave = _chave_publica()
	except DataJudError:
		return
	if not _circuito_permite_execucao(config):
		return

	coletor = _ColetorErros()
	saudavel, tipo_falha_saude = _verificar_saude(chave, coletor)
	if not saudavel:
		_abrir_ou_manter_circuito(config, tipo_falha_saude)
		coletor.persistir()
		config.save(ignore_permissions=True)
		frappe.db.commit()
		return

	processos = frappe.get_all(
		"Processo Judicial",
		filters={"status_processo": "Em andamento"},
		fields=["numero_processo", "tribunal"],
	)
	pares = {
		(p.numero_processo, _alias_do_tribunal(p.tribunal))
		for p in processos
		if _alias_do_tribunal(p.tribunal)
	}

	inicio = time.monotonic()
	houve_sucesso = False
	for numero, alias in pares:
		if time.monotonic() - inicio > ORCAMENTO_LOTE_SEGUNDOS:
			# O restante fica para a próxima janela do cron; não trava o worker indefinidamente.
			break
		if atualizar_um_processo(
			numero, alias, chave=chave, timeout=TIMEOUT_LOTE, tentativas=1, coletor=coletor
		):
			houve_sucesso = True

	if coletor.grupos:
		coletor.persistir()
		_abrir_ou_manter_circuito(config, coletor.tipo_predominante())
	elif houve_sucesso:
		_fechar_circuito_se_necessario(config)
	if houve_sucesso:
		config.ultima_sincronizacao_sucesso = now_datetime()
	config.save(ignore_permissions=True)
	frappe.db.commit()
