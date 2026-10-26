"""Leitura do "Relatório geral de PDC" (PDF) exportado pelo Bionexo.

Função pura, sem banco: ``parse_relatorio(pdf_bytes)`` (ou ``parse_texto(texto)`` para testes) devolve o
cabeçalho da cotação, os itens com as respostas de cada fornecedor e a tabela de fornecedores participantes,
com o CNPJ de cada resposta resolvido pelo nome do fornecedor.
"""

import html
import io
import re
import unicodedata

RE_CNPJ = re.compile(r"^[0-9A-Z]{2}\.[0-9A-Z]{3}\.[0-9A-Z]{3}/[0-9A-Z]{4}-\d{2}$")
RE_ITEM = re.compile(r"^(\d+) Código$")
RE_CABECALHO_RESPOSTA = re.compile(r"^Fornecedor Informações do produto")
RE_VALORES = re.compile(r"^([\d.,]+) R\$ ?([\d.]+,\d+) R\$ ?([\d.]+,\d+) (.+)$")
RE_FIM_PARTICIPANTE = re.compile(r"^(\d{2}/\d{2}/\d{4}) (.*?) ?([\d.]+,\d{2})$")
RE_CONFIRMADO = re.compile(r"^(.+) (\d+) ([\d.]+,\d{2})$")
RE_DATA = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
RE_DATA_CONFIRMACAO = re.compile(r"no dia (\d{2})/(\d{2})/(\d{4}) às (\d{2})h(\d{2})m")
RE_TELEFONE = re.compile(r"^\(?\d{2}\)? ?[\d.\- ]{7,}$|^\d{6,}-\d{4}$")

INICIO_PARTICIPANTES = "Fornecedores participantes desta cotação"
INICIO_RESUMO = "Resumo dos valores por fornecedor"
ROTULOS_RESPOSTA = ("Confirmado por:", "Observação do fornecedor:", "Justificativa de escolha:")
CHAVES_ROTULO = {
	"Confirmado por:": "confirmado_por",
	"Observação do fornecedor:": "observacao",
	"Justificativa de escolha:": "justificativa",
}


def parse_relatorio(pdf_bytes: bytes) -> dict:
	from pypdf import PdfReader

	leitor = PdfReader(io.BytesIO(pdf_bytes))
	return parse_texto("\n".join(pagina.extract_text() or "" for pagina in leitor.pages))


def parse_texto(texto: str) -> dict:
	linhas = _linhas(texto)
	if not any(RE_ITEM.match(linha) for linha in linhas):
		raise ValueError(
			"O arquivo não parece ser um Relatório geral de PDC do Bionexo (nenhum item encontrado)."
		)

	dados = _cabecalho(texto, linhas)
	i_participantes = _indice(linhas, INICIO_PARTICIPANTES, len(linhas))
	dados["itens"] = _itens(linhas[:i_participantes])
	dados["participantes"] = _participantes(linhas[i_participantes:])
	dados["confirmados"] = _confirmados(linhas[i_participantes:])

	por_chave = {chave_nome(p["nome"]): p for p in dados["participantes"]}
	for item in dados["itens"]:
		for resposta in item["respostas"]:
			participante = _participante_por_nome(por_chave, resposta["fornecedor"])
			resposta["cnpj"] = participante["cnpj"] if participante else ""
	return dados


def chave_nome(nome: str) -> str:
	"""Nome sem acento, espaço e pontuação: o PDF cola palavras ("Ello DistribuicaoLtda")."""
	sem_acento = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode()
	return re.sub(r"[^a-z0-9]", "", sem_acento.lower())


def numero_br(valor: str) -> float:
	valor = (valor or "").strip()
	if not valor:
		return 0.0
	if "," in valor:
		valor = valor.replace(".", "").replace(",", ".")
	elif re.fullmatch(r"\d{1,3}(\.\d{3})+", valor):
		valor = valor.replace(".", "")
	return float(valor)


def data_iso(valor: str) -> str | None:
	achado = RE_DATA.search(valor or "")
	if not achado:
		return None
	dia, mes, ano = achado.groups()
	return f"{ano}-{mes}-{dia}"


def _linhas(texto: str) -> list[str]:
	texto = unicodedata.normalize("NFC", html.unescape(texto or ""))
	linhas = (re.sub(r"[ \t\xa0]+", " ", linha).strip() for linha in texto.splitlines())
	return [linha for linha in linhas if linha]


def _indice(linhas, valor, padrao=None):
	for i, linha in enumerate(linhas):
		if linha == valor:
			return i
	return padrao


def _linha_apos(linhas, rotulo):
	i = _indice(linhas, rotulo)
	return linhas[i + 1] if i is not None and i + 1 < len(linhas) else ""


def _busca(padrao, texto):
	achado = re.search(padrao, texto)
	return achado.group(1).strip() if achado else ""


def _cabecalho(texto, linhas):
	observacoes = []
	i = _indice(linhas, "Observações")
	if i is not None:
		for linha in linhas[i + 1 :]:
			if linha == "Termos e condições" or RE_ITEM.match(linha):
				break
			observacoes.append(linha)
	return {
		"id_cotacao": _busca(r"\bID: ?(\d+)", texto),
		"id_upload": _busca(r"ID do upload: ?(\d+)", texto),
		"titulo": _busca(r"Título: ?(.+)", texto),
		"criado_por": _busca(r"Criado por: ?(.+)", texto),
		"data_criacao": data_iso(_linha_apos(linhas, "Data de criação")),
		"vencimento": data_iso(_linha_apos(linhas, "Vencimento")),
		"forma_pagamento": _linha_apos(linhas, "Forma de pagamento"),
		"observacoes": "\n".join(observacoes),
	}


def _itens(linhas):
	itens = []
	i = 0
	while i < len(linhas):
		achado = RE_ITEM.match(linhas[i])
		if not achado:
			i += 1
			continue
		item = {
			"seq": int(achado.group(1)),
			"codigo": linhas[i + 1],
			"descricao": "",
			"unidade": "",
			"qtd_solicitada": 0.0,
			"respostas": [],
		}
		j = i + 2
		if j < len(linhas) and re.match(r"^Nome do ?item$", linhas[j]):
			j += 1
		nome = []
		while j < len(linhas) and linhas[j] != "Embalagem":
			nome.append(linhas[j])
			j += 1
		descricao, _, unidade = " ".join(nome).rpartition(" | ")
		item["descricao"] = (descricao or unidade).strip()
		item["unidade"] = (linhas[j + 1] if j + 1 < len(linhas) else unidade).strip()
		k = _indice(linhas[j:], "Qntd. solicitada")
		if k is not None and j + k + 1 < len(linhas):
			item["qtd_solicitada"] = numero_br(linhas[j + k + 1])

		fim = next((n for n in range(j, len(linhas)) if RE_ITEM.match(linhas[n])), len(linhas))
		inicios = [n for n in range(j, fim) if RE_CABECALHO_RESPOSTA.match(linhas[n])]
		for a, b in zip(inicios, [*inicios[1:], fim], strict=True):
			resposta = _resposta(linhas[a + 1 : b])
			if resposta:
				item["respostas"].append(resposta)
		itens.append(item)
		i = fim
	return itens


def _resposta(bloco):
	i_valores = next((n for n, linha in enumerate(bloco) if RE_VALORES.match(linha)), None)
	if i_valores is None:
		return None
	qty, rate, amount, status = RE_VALORES.match(bloco[i_valores]).groups()

	produto = bloco[:i_valores]
	i_item = next((n for n, linha in enumerate(produto) if "Item:" in linha), len(produto))
	nome = produto[:i_item]
	if i_item < len(produto):
		antes, _, depois = produto[i_item].partition("Item:")
		if antes.strip():
			nome.append(antes.strip())
		produto = ["Item:" + depois, *produto[i_item + 1 :]]
	else:
		produto = []
	campos = _por_rotulo(" ".join(produto), ("Item:", "Marca:", "Embalagem:"))

	resto = " ".join(bloco[i_valores + 1 :])
	extras = _por_rotulo(resto, ROTULOS_RESPOSTA)

	resposta = {
		"fornecedor": " ".join(nome).strip(),
		"qty": numero_br(qty),
		"rate": numero_br(rate),
		"amount": numero_br(amount),
		"status": status.strip(),
		"item_fornecedor": campos.get("Item:", ""),
		"marca": campos.get("Marca:", ""),
		"embalagem": campos.get("Embalagem:", ""),
	}
	for rotulo, chave in CHAVES_ROTULO.items():
		resposta[chave] = extras.get(rotulo, "")
	resposta["data_confirmacao"] = data_confirmacao(resposta["confirmado_por"])
	return resposta


def data_confirmacao(confirmado_por: str) -> str | None:
	"""'Fulana no dia 20/10/2026 às 16h28m' -> '2026-10-20 16:28:00'."""
	achado = RE_DATA_CONFIRMACAO.search(confirmado_por or "")
	if not achado:
		return None
	dia, mes, ano, hora, minuto = achado.groups()
	return f"{ano}-{mes}-{dia} {hora}:{minuto}:00"


def _por_rotulo(texto, rotulos):
	"""{rótulo: valor} para "Rótulo: valor Outro: valor"; "-" e "." viram vazio."""
	padrao = "|".join(re.escape(r) for r in rotulos)
	partes = re.split(f"({padrao})", texto)
	valores = {}
	for rotulo, valor in zip(partes[1::2], partes[2::2], strict=True):
		valor = valor.strip()
		valores[rotulo] = "" if valor in ("-", ".") else valor
	return valores


def _participantes(linhas):
	participantes = []
	bloco = []
	for linha in linhas[1:]:
		if linha == INICIO_RESUMO:
			break
		if linha.startswith("Fornecedor e CNPJ"):
			continue
		achado = RE_FIM_PARTICIPANTE.match(linha)
		if not achado:
			bloco.append(linha)
			continue
		participante = _participante(bloco, *achado.groups())
		if participante:
			participantes.append(participante)
		bloco = []
	return participantes


def _participante(bloco, validade, pagamento, minimo):
	i_cnpj = next((n for n, linha in enumerate(bloco) if RE_CNPJ.match(linha)), None)
	if i_cnpj is None:
		return None
	contato = [linha for linha in bloco[i_cnpj + 1 :] if not linha.startswith(("Frete:", "Entrega:"))]
	envio = {
		k.rstrip(":"): v.strip()
		for k, _, v in (linha.partition(" ") for linha in bloco if linha.startswith(("Frete:", "Entrega:")))
	}
	email = next((linha for linha in contato if "@" in linha), "")
	telefone = next((linha for linha in contato if RE_TELEFONE.match(linha)), "")
	return {
		"nome": " ".join(bloco[:i_cnpj]),
		"cnpj": bloco[i_cnpj],
		"contato": " ".join(linha for linha in contato if linha not in (email, telefone)),
		"email": email,
		"telefone": telefone,
		"frete": envio.get("Frete", ""),
		"entrega": envio.get("Entrega", ""),
		"validade": data_iso(validade),
		"pagamento": pagamento.strip(),
		"faturamento_minimo": numero_br(minimo),
	}


def _participante_por_nome(por_chave, nome):
	chave = chave_nome(nome)
	if chave in por_chave:
		return por_chave[chave]
	candidatos = [p for k, p in por_chave.items() if chave and (k.startswith(chave) or chave.startswith(k))]
	return candidatos[0] if len(candidatos) == 1 else None


def _confirmados(linhas):
	i = _indice(linhas, "Itens confirmados")
	if i is None:
		return []
	confirmados = []
	for linha in linhas[i + 1 :]:
		if linha.startswith("Total de fornecedores"):
			break
		achado = RE_CONFIRMADO.match(linha)
		if achado and not linha.startswith("Fornecedor Número"):
			nome, quantidade, total = achado.groups()
			confirmados.append({"nome": nome, "itens": int(quantidade), "total": numero_br(total)})
	return confirmados
