# ADR-001: Leitura mínima garantida em DocTypes vinculados por Link

## Contexto
O Jurídico (`Processo Judicial` e suas tabelas filhas) referencia, por campos Link e Dynamic Link, DocTypes
padrão de outros apps instalados na bench (ERPNext, HRMS): `Company` e `Currency` (Link, em `Processo Judicial`)
e, via `Dynamic Link` em `Processo Judicial Parte` (`tipo_parte`), `Employee`, `Customer` e `Supplier` — além de
"Terceiros" (pacientes), ligados a `Contact`. O papel próprio deste app para o módulo, **Usuário Jurídico**
(`integracoes_customizadas/fixtures/role.json`), só tem permissão própria sobre os DocTypes do próprio Jurídico
(`processo_judicial.json`: `Usuário Jurídico` e `System Manager`); não há nenhuma fixture `Custom DocPerm` neste
app hoje (`integracoes_customizadas/fixtures/` só tem `custom_field.json`, `custom_html_block.json` e
`role.json`). A leitura de `Employee`, `Customer`, `Supplier` e `Contact` por quem só tem `Usuário Jurídico`
depende, portanto, inteiramente de um papel de outro módulo (RH, Vendas, Compras) já conceder leitura — o mesmo
padrão que, no `clm`, deixava o usuário base travado no meio do fluxo com um Link vazio ou erro de permissão ao
abrir o registro referenciado, sem indício de que a causa era de outro módulo (ver, no repositório `clm`,
`docs/adr-006-leitura-minima-em-doctypes-vinculados.md`, que corrigiu o mesmo problema para `CLM User` com
fixtures `Custom DocPerm` aditivas).

As demais frentes do app não criam papel próprio: Compras usa deliberadamente os papéis padrão do ERPNext
(`Stock User`, `Purchase User`/`Manager`, `Accounts User`/`Manager` — ver [fluxo-compras.md](fluxo-compras.md)),
que já têm leitura garantida nos DocTypes que usam porque são os papéis "donos" desses cadastros; o WhatsApp e o
Provas não expõem Link para fora do próprio módulo em volume relevante. O princípio desta ADR vale igualmente
para elas caso ganhem, no futuro, um papel próprio com Link para fora do seu módulo.

## Decisão
Toda vez que um DocType deste app ganha um campo Link ou Dynamic Link para um DocType de outro módulo/app —
ERPNext, HRMS, `busca_cnpj`, `rh_brasil`, `clm` ou `assinatura_eletronica` —, o papel de uso básico/diário
daquele fluxo (hoje, **Usuário Jurídico** para o Jurídico) deve ter, no mínimo, permissão de leitura (`read`,
que cobre o uso em dropdowns de Link e Dynamic Link — equivalente ou superior a `select`) sobre o DocType
referenciado, independentemente de qualquer papel de outro módulo conceder essa leitura. Isso é implementado
como fixture `Custom DocPerm` registrada em `fixtures/` e em `hooks.py`, nunca editando o DocType do outro app.

`Custom DocPerm` é **aditiva**: soma uma linha de permissão ao DocType de outro app, não substitui nem remove
as permissões padrão que esse DocType já tem para outros papéis — é o mesmo mecanismo usado pelo `clm` na
ADR-006 citada acima, sem efeito colateral sobre quem já lê o cadastro por outro papel. (Essa confusão aparecia
em [fluxo-compras.md](fluxo-compras.md) como motivo para não usar `Custom DocPerm`; foi corrigida no mesmo
commit desta ADR.)

Ao adicionar um campo Link/Dynamic Link para um DocType fora do app em qualquer DocType deste repositório, a
mudança só está completa quando a fixture de leitura existir para esse DocType (ou já existir de uma mudança
anterior) para o(s) papel(éis) básico(s) do fluxo afetado.

## Achado ao redigir esta ADR (pendência, não corrigida aqui)
Esta tarefa é só documentação — nenhuma permissão foi alterada. Ao revisar o estado atual:

- `Processo Judicial Parte.tipo_parte` liga, por Dynamic Link, a `Employee`, `Customer` e `Supplier` (e a
  `Contact`, para "Terceiros"). `Usuário Jurídico` não tem fixture própria de leitura sobre nenhum desses quatro
  DocTypes; a leitura hoje depende de esse papel também ter (ou um usuário acumular) um papel de RH, Vendas ou
  Compras — exatamente o padrão implícito que a ADR-006 do `clm` identificou como causa de bloqueio no meio do
  fluxo. Não foi possível confirmar nesta sessão, sem o código-fonte do `erpnext`/`hrms` disponível localmente,
  se algum desses DocTypes concede leitura a `Usuário Jurídico` por outra via (ex.: papel `All` com leitura
  ampla); fica como pendência verificar e, se confirmada a lacuna, abrir a fixture `Custom DocPerm`
  correspondente em uma mudança própria (fora do escopo desta tarefa).
- `Supplier`, preenchido pela importação Bionexo via consulta de CNPJ do `busca_cnpj`
  (`bionexo/import_pdf.py`), é lido/criado pelos papéis padrão de Compras (`Purchase User`/`Manager`), que já
  têm permissão própria sobre `Supplier` no ERPNext — não há lacuna aqui, pois este app não introduz um papel
  próprio para esse fluxo.
- `rh_brasil.documentos` (usado em `juridico/doctype/processo_judicial/processo_judicial.py` e `juridico/parte.py`
  via `format_cpf`) é um módulo de funções utilitárias, não um DocType — não há campo Link para um DocType do
  `rh_brasil` neste app hoje, então não se aplica a este achado.

## Consequências
- Quando a fixture de leitura mínima for de fato criada para os DocTypes acima, nenhum fluxo do Jurídico deve
  travar o usuário base por falta de leitura num cadastro vinculado de outro módulo: a dependência cruzada deixa
  de ser implícita e passa a ser explícita e garantida pelo próprio `integracoes_customizadas`.
- O alcance pretendido é só leitura: `write`, `create` e `delete` desses DocTypes continuam fora do escopo deste
  app e seguem governados pelos papéis que já os administram (RH, Vendas, Compras etc.).
- Revisão de PR: toda PR que introduz um campo Link/Dynamic Link para um DocType externo ao app deve checar se
  a fixture de leitura já cobre esse DocType para o papel básico do fluxo; se não, adicioná-la no mesmo commit
  (ou, se for apenas constatada e não corrigida, registrar a lacuna como pendência explícita, como feito acima).
