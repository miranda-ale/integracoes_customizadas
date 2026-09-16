"""Consulta e espelhamento dos metadados públicos do DataJud."""

import hashlib
import re
import secrets
import time
from collections import Counter

import frappe
import requests
from frappe import _


TRIBUNAIS = (
	"stj", "stm", "tse", "tst",
	*(f"trf{numero}" for numero in range(1, 7)),
	"tjac", "tjal", "tjam", "tjap", "tjba", "tjce", "tjdft", "tjes", "tjgo",
	"tjma", "tjmg", "tjms", "tjmt", "tjpa", "tjpb", "tjpe", "tjpi", "tjpr",
	"tjrj", "tjrn", "tjro", "tjrr", "tjrs", "tjsc", "tjse", "tjsp", "tjto",
	*(f"trt{numero}" for numero in range(1, 25)),
	*(f"tre-{uf}" for uf in (
		"ac", "al", "am", "ap", "ba", "ce", "dft", "es", "go", "ma", "mg", "ms", "mt",
		"pa", "pb", "pe", "pi", "pr", "rj", "rn", "ro", "rr", "rs", "sc", "se", "sp", "to",
	)),
	"tjmmg", "tjmrs", "tjmsp",
)

API_BASE = "https://api-publica.datajud.cnj.jus.br"
PAGE_SIZE = 100


class DataJudError(Exception):
	pass


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


def _post(alias, payload, chave):
	url = f"{API_BASE}/api_publica_{alias}/_search"
	for tentativa in range(3):
		try:
			resposta = requests.post(
				url,
				headers={"Authorization": f"APIKey {chave}", "Content-Type": "application/json"},
				json=payload,
				timeout=20,
			)
		except requests.RequestException as exc:
			if tentativa == 2:
				raise DataJudError(_("Não foi possível conectar ao DataJud.")) from exc
		else:
			if resposta.status_code == 401 or resposta.status_code == 403:
				raise DataJudError(_("Chave pública do DataJud recusada."))
			if resposta.status_code < 400:
				try:
					conteudo = resposta.json()
				except ValueError as exc:
					raise DataJudError(_("Resposta JSON inválida do DataJud.")) from exc
				if not isinstance(conteudo, dict):
					raise DataJudError(_("Resposta inesperada do DataJud."))
				if conteudo.get("timed_out") or (conteudo.get("_shards") or {}).get("failed", 0):
					if tentativa == 2:
						raise DataJudError(_("A pesquisa no DataJud retornou resultado incompleto."))
					time.sleep(2**tentativa)
					continue
				return conteudo
			if resposta.status_code != 429 and resposta.status_code < 500:
				raise DataJudError(_("Consulta DataJud falhou (HTTP {0}).").format(resposta.status_code))
			if tentativa == 2:
				raise DataJudError(_("DataJud indisponível (HTTP {0}).").format(resposta.status_code))
		time.sleep(2**tentativa)
	raise DataJudError(_("Consulta DataJud não concluída."))


def consultar_numero(numero, alias, chave=None):
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
		resposta = _post(alias, consulta, chave)
		if resposta.get("timed_out") or resposta.get("_shards", {}).get("failed", 0):
			raise DataJudError(_("A pesquisa no DataJud retornou resultado incompleto."))
		try:
			pagina = resposta["hits"]["hits"]
			if not isinstance(pagina, list):
				raise TypeError
		except (KeyError, TypeError) as exc:
			raise DataJudError(_("Resposta inesperada do DataJud.")) from exc
		for hit in pagina:
			fonte = hit.get("_source") or {}
			if fonte.get("numeroProcesso") == numero and _alias_do_tribunal(fonte.get("tribunal")) == alias:
				identificador = fonte.get("id") or hit.get("_id")
				if not isinstance(identificador, str) or not identificador:
					raise DataJudError(_("Ocorrência sem ID na resposta do DataJud."))
				if identificador not in identificadores:
					resultados.append((identificador, fonte))
					identificadores.add(identificador)
		if len(pagina) < PAGE_SIZE:
			break
		cursor = pagina[-1].get("sort")
		if not cursor or cursor == ultimo_cursor:
			raise DataJudError(_("Paginação inválida na resposta do DataJud."))
		ultimo_cursor = cursor
	return resultados


def _preencher_ocorrencia(doc, identificador, fonte, *, registrar_assuntos=True):
	doc.update({
		"datajud_id": identificador,
		"numero_processo": _numero_cnj_formatado(fonte.get("numeroProcesso")),
		"tribunal": fonte.get("tribunal"),
		"grau": fonte.get("grau"),
		"nivel_sigilo": fonte.get("nivelSigilo"),
		"data_ajuizamento_original": fonte.get("dataAjuizamento"),
		"data_hora_ultima_atualizacao_original": fonte.get("dataHoraUltimaAtualizacao"),
		"timestamp_original": fonte.get("@timestamp"),
	})
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
		doc.append("assuntos", {
			"assunto": (
				_registrar_assunto(assunto.get("codigo"), assunto.get("nome"))
				if registrar_assuntos else _id_assunto(assunto.get("codigo"), assunto.get("nome"))
			),
			"codigo": assunto.get("codigo"),
			"nome": assunto.get("nome"),
		})
	doc.set("movimentos", [])
	for movimento in fonte.get("movimentos") or []:
		orgao_movimento = movimento.get("orgaoJulgador") or {}
		doc.append("movimentos", {
			"codigo": movimento.get("codigo"),
			"nome": movimento.get("nome"),
			"data_hora_original": movimento.get("dataHora"),
			"orgao_julgador_codigo": orgao_movimento.get("codigoOrgao", orgao_movimento.get("codigo")),
			"orgao_julgador_nome": orgao_movimento.get("nomeOrgao", orgao_movimento.get("nome")),
			"complementos_tabelados": movimento.get("complementosTabelados") or [],
		})
	doc._atualizar_dados_datajud()
	return doc


def _id_assunto(codigo, nome):
	return str(codigo) if codigo is not None and codigo != "" else (
		"nome-" + hashlib.sha1((nome or "").encode()).hexdigest()[:16]
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
			f"datajud-rascunho:{token}", {"usuario": frappe.session.user, "fonte": fonte, "identificador": identificador},
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
			movimento.codigo, movimento.nome, movimento.data_hora_original,
			movimento.orgao_julgador_codigo, movimento.orgao_julgador_nome,
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


def atualizar_processos_acompanhados():
	"""Distribui as consultas para a fila longa sem exceder o tempo do cron."""
	try:
		_chave_publica()
	except DataJudError:
		return
	processos = frappe.get_all(
		"Processo Judicial", filters={"status_processo": "Em andamento"},
		fields=["numero_processo", "tribunal"],
	)
	pares = {(p.numero_processo, _alias_do_tribunal(p.tribunal)) for p in processos}
	for numero, alias in pares:
		job_id = "datajud-" + hashlib.sha256(f"{alias}:{numero}".encode()).hexdigest()[:24]
		frappe.enqueue(
			"integracoes_customizadas.juridico.datajud.atualizar_um_processo",
			queue="long",
			timeout=900,
			deduplicate=True,
			job_id=job_id,
			enqueue_after_commit=True,
			numero=numero,
			alias=alias,
		)


def _ids_em_andamento(numero, alias):
	"""Identifica as ocorrências ainda acompanhadas desse número e tribunal."""
	processos = frappe.get_all(
		"Processo Judicial",
		filters={"numero_processo": _numero_cnj_formatado(numero), "status_processo": "Em andamento"},
		fields=["datajud_id", "tribunal"],
	)
	return {p.datajud_id for p in processos if _alias_do_tribunal(p.tribunal) == alias}


def atualizar_um_processo(numero, alias):
	"""Atualiza ocorrências acompanhadas; preserva dados anteriores em caso de falha."""
	if not _ids_em_andamento(numero, alias):
		return
	frappe.db.savepoint("datajud_consulta")
	try:
		for identificador, fonte in consultar_numero(numero, alias):
			ativos = _ids_em_andamento(numero, alias)
			if not ativos:
				break
			existente = frappe.db.exists("Processo Judicial", {"datajud_id": identificador})
			if existente and identificador not in ativos:
				continue
			_espelhar_ocorrencia(identificador, fonte)
	except Exception as exc:
		frappe.db.rollback(save_point="datajud_consulta")
		frappe.log_error(
			title="Falha na atualização DataJud",
			message=f"Processo {numero}, tribunal {alias}: {type(exc).__name__}. Dados anteriores preservados.",
		)
