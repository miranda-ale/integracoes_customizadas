# Integração API Pública Datajud (CNJ)

## Objetivo

Consultar metadados de processos judiciais na base nacional Datajud (Resolução CNJ n. 331/2020) pelo **número único CNJ** (20 dígitos), preenchendo o formulário de Processo Judicial e as tabelas filhas (eventos, integração).

## Documentação oficial

- [Datajud-Wiki](https://datajud-wiki.cnj.jus.br/)
- [API Pública — Endpoints](https://datajud-wiki.cnj.jus.br/api-publica/endpoints/)
- [Glossário de Dados](https://datajud-wiki.cnj.jus.br/api-publica/glossario/)

## O que é o Datajud

O Datajud é a base nacional de metadados processuais do Poder Judiciário brasileiro. A API Pública permite consultar processos por número único (CNJ), retornando capa processual e movimentações conforme o Modelo de Transferência de Dados (MTD) e a Portaria nº 160/2020.

## Configuração

### 1. Conta e chave API

- É necessário obter uma **Chave Pública (API Key)** no portal do Datajud/CNJ.
- A chave é enviada no cabeçalho: `Authorization: APIKey <Chave Pública>`.

### 2. Onde configurar a chave

- **Recomendado:** em `site_config.json` (não versionado):

  ```json
  {
    "datajud_api_key": "SUA_CHAVE_PUBLICA_DATAJUD"
  }
  ```

- **Opcional:** DocType "Configuracoes Contencioso" com campo `datajud_api_key` (se existir e estiver implementado).

- **Nunca** commitar a chave em repositório.

### 3. Habilitar integração

- Para que a consulta à API seja feita, defina em `site_config.json`:

  ```json
  {
    "contencioso_integracao_ativa": true
  }
  ```

  Se `contencioso_integracao_ativa` for `false` ou não estiver definido, a busca no Datajud não será executada (evita chamadas em ambiente sem credencial).

## Uso no formulário

1. **Número CNJ:** o campo aceita apenas dígitos e exibe a máscara `NNNNNNN-DD.AAAA.J.TR.OOOO`. O valor é armazenado com 20 dígitos (sem formatação) para compatibilidade com a API.
2. **Botão "Buscar no Datajud":** no grupo "Identificação do Processo", ao clicar:
   - o número é normalizado para 20 dígitos;
   - é chamado o método whitelisted `buscar_processo_para_form`;
   - os campos da capa (tribunal, classe, assuntos, vara/foro, data de distribuição, nível de sigilo, etc.) e as tabelas **Eventos** e **Integrações** são preenchidos com os dados retornados.

## Mapeamento (glossário API → Processo Judicial)

| Campo API (glossário) | Campo DocType |
|------------------------|---------------|
| numeroProcesso | cj_numero_cnj (20 dígitos) |
| dataAjuizamento | cj_data_distribuicao |
| tribunal | cj_tribunal |
| classe.nome | cj_classe |
| assuntos[].nome | cj_assuntos (texto, um por linha) |
| orgaoJulgador.nome | cj_vara_foro |
| nivelSigilo (0–5) | cj_nivel_sigilo (Publico / Restrito / Sigiloso) |

**Movimentações:** cada item de `movimentos[]` vira uma linha em **CJ Evento** com origem "Integração", tipo "Movimento", e `cj_id_externo` para idempotência.

**Integração:** uma linha em **CJ Integracao** com provedor "DataJud", chave externa (id do hit ou numeroProcesso), status "OK" e log "Consulta por número CNJ".

## Referência MTD 1.2

O Modelo de Transferência de Dados (MTD) 1.2 (XML) define os tipos completos para envio pelos tribunais ao CNJ (partes, documentos, valor da causa, etc.). A API Pública expõe um subconjunto (glossário). Esta integração usa esse subconjunto; expansões futuras (partes, documentos) podem seguir o MTD 1.2 como referência.

## Segurança

- Apenas o método `buscar_processo_para_form` é whitelisted; o cliente HTTP não é exposto diretamente.
- A chave API não deve aparecer em logs nem em mensagens ao usuário.

## Testes

Os testes unitários cobrem `cnj_to_tribunal_alias()` (TRT2, TJSP, TRF1, etc.) e o mapeamento da resposta da API para Processo Judicial e CJ Evento (mock do glossário). Para rodar:

```bash
bench run-tests integracoes_customizadas.contencioso.integracoes.tests.test_datajud
```
