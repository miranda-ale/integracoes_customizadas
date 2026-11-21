# ADR-002: Qualidade e legibilidade de logs de integração externa

## Contexto

A integração com a API Pública do DataJud (CNJ) passou a falhar com HTTP 403 em todos os tribunais — causa
externa, até com a chave pública oficial do CNJ. O Error Log existente só registrava
`"Processo X, tribunal Y: DataJudError. Dados anteriores preservados."`: sem endpoint, método, status HTTP, corpo
da resposta ou traceback. Diagnosticar a causa raiz exigiu ler o código-fonte, não o log. Ao mesmo tempo, cada
processo falhando virava um registro próprio a cada execução — com 56 processos falhando, eram 56 entradas por
rodada, inundando o Error Log e escondendo o sinal (qual é o erro real) no ruído (quantas vezes ele se repetiu).

Ver [docs/datajud-qualidade-de-logs.md](datajud-qualidade-de-logs.md) para a correção completa aplicada ao DataJud.

## Decisão

Toda integração com um serviço externo (API de terceiro, webhook, fila) deste app deve logar o suficiente para
diagnosticar a causa sem precisar reler o código-fonte, e sem inundar o Error Log:

1. **Contexto estruturado, não só a mensagem da exceção**: endpoint/URL, método HTTP, status HTTP, tempo de
   resposta, os primeiros ~1.000 caracteres do corpo da resposta, o tipo da exceção e o traceback — tudo que o
   DataJud passou a gravar em `DataJud Sync Log` é o piso esperado, não um caso especial daquela integração.
2. **Nunca gravar segredo em claro**: chave de API, token, senha ou header `Authorization` completo nunca vão para
   o log; quando é útil confirmar *qual* chave foi usada (ex.: durante rotação), grava-se só um prefixo mascarado
   (ver `_mascarar_chave` em `juridico/datajud.py`).
3. **Classificar o erro**, não só repetir a exceção crua: pelo menos autenticação/autorização, limite de
   requisições, não encontrado, indisponibilidade e dados inválidos são categorias distintas o bastante para
   decidir a ação (trocar a chave vs. esperar vs. nada a fazer).
4. **Agrupar falhas repetidas da mesma execução por tipo de erro**, com contagem e a lista dos registros afetados,
   em vez de um registro por item processado. Uma falha sistêmica (a API inteira fora do ar) deve gerar poucos
   registros de log claros, não uma entrada por processo/registro/linha a cada execução.
5. **Resumir o estado atual num lugar visível** (último sucesso, último erro, status do último erro, falhas
   consecutivas) no próprio cadastro de configuração da integração, para que confirmar "está funcionando?" não
   exija abrir o Error Log.

Esta diretriz é o motivo por trás do design do DataJud (`DataJud Sync Log` + resumo em `DataJud Settings`) e
vale para qualquer integração externa futura ou existente neste app (WhatsApp/Evolution, Bionexo, `busca_cnpj`
etc.): ao tocar numa integração externa por outro motivo, aproveite para alinhar o log dela a este padrão.

## Consequências

- Revisão de PR: uma integração externa nova ou alterada que só grava `frappe.log_error(str(exc))` sem status
  HTTP/corpo/classificação não está completa.
- Isso não troca `frappe.log_error` por um DocType próprio em todo lugar — API/webhooks simples, de baixo volume
  de falha, continuam podendo usar o Error Log, desde que com o contexto estruturado do item 1. Um DocType próprio
  (como `DataJud Sync Log`) se justifica quando o volume de falhas por execução pede agrupamento (item 4) ou
  quando o resumo do item 5 precisa de campos consultáveis.
