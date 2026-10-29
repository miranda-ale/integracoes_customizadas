/* global root_element */
const grade = root_element.querySelector(".ind-grade");
const assuntos = root_element.querySelector(".ind-assuntos");
const rodape = root_element.querySelector(".ind-rodape");
const seletor = root_element.querySelector(".ind-unidade");
const esc = (v) => frappe.utils.escape_html(String(v ?? ""));
const num = (v) => Number(v || 0).toLocaleString("pt-BR");
const brl = (v) => Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function tile({ titulo, valor, detalhe, rota, alerta, aviso }) {
	return `<a class="ind-tile ${alerta ? "ind-alerta" : ""}" href="${rota}" ${
		alerta ? 'role="alert"' : ""
	}>
		<div class="ind-titulo">${esc(titulo)}${
		alerta ? '<span class="ind-selo">⚠ Atenção</span>' : ""
	}</div>
		<div class="ind-valor">${esc(valor)}</div>
		<div class="ind-detalhe">${detalhe}</div>
		${alerta ? `<div class="ind-aviso">${esc(aviso)}</div>` : ""}
	</a>`;
}

function render(d) {
	const lista = "/app/processo-judicial";
	const tiles = [
		tile({
			titulo: "Processos em andamento",
			valor: num(d.andamento),
			detalhe: `Valor das causas: ${brl(d.valor_andamento)}`,
			rota: `${lista}?status_processo=Em%20andamento`,
		}),
		tile({
			titulo: "Processos encerrados",
			valor: num(d.encerrados),
			detalhe: `Total cadastrado: ${num(d.total)}`,
			rota: `${lista}?status_processo=Encerrado`,
		}),
		tile({
			titulo: "Novos processos",
			valor: num(d.novos),
			detalhe: `Nos últimos ${d.dias_novos} dias`,
			rota: lista,
		}),
		tile({
			titulo: "Risco alto",
			valor: num(d.risco_alto),
			detalhe: "Em andamento classificados como risco alto",
			rota: `${lista}?risco=Alto&status_processo=Em%20andamento`,
			alerta: d.risco_alto > 0,
			aviso: "Processos de risco alto em andamento",
		}),
		tile({
			titulo: "Sem atualização",
			valor: num(d.sem_atualizacao),
			detalhe: `Em andamento sem atualização há mais de ${d.dias_sem_atualizacao} dias`,
			rota: `${lista}?status_processo=Em%20andamento`,
			alerta: d.sem_atualizacao > 0,
			aviso: "Verifique a consulta ao DataJud",
		}),
		tile({
			titulo: "Cadastros em rascunho",
			valor: num(d.rascunhos),
			detalhe: "Processos consultados e ainda não cadastrados",
			rota: `${lista}?situacao_cadastro=Rascunho`,
		}),
	];
	if (d.pareceres) {
		tiles.push(
			tile({
				titulo: "Pareceres jurídicos",
				valor: num(d.pareceres.emitidos),
				detalhe: `${num(d.pareceres.rascunho)} em rascunho`,
				rota: "/app/clm-legal-evaluation",
			})
		);
	}
	grade.innerHTML = tiles.join("");

	const maximo = Math.max(1, ...d.assuntos.map((a) => a.total));
	assuntos.innerHTML = d.assuntos.length
		? `<h6>Assuntos mais frequentes</h6>` +
		  d.assuntos
				.map(
					(a) => `<div class="ind-barra"><span>${esc(a.assunto)}</span>
				<div class="ind-barra-fundo"><div class="ind-barra-fill" style="width:${
					(a.total / maximo) * 100
				}%"></div></div><span>${num(a.total)}</span></div>`
				)
				.join("")
		: "";
	rodape.textContent = `${d.referencia} · Alertas: risco alto e processos sem atualização`;
}

function carregar() {
	grade.innerHTML = '<div class="ind-vazio">Carregando…</div>';
	frappe
		.xcall("integracoes_customizadas.juridico.indicadores.get_dashboard", {
			company: seletor.value || null,
		})
		.then(render)
		.catch(() => {
			grade.innerHTML =
				'<div class="ind-vazio">Não foi possível carregar os indicadores.</div>';
		});
}

frappe.db
	.get_list("Company", { fields: ["name"], limit: 0, order_by: "name asc" })
	.then((rows) => {
		seletor.innerHTML =
			'<option value="">Todas as unidades</option>' +
			rows.map((r) => `<option value="${esc(r.name)}">${esc(r.name)}</option>`).join("");
	});
seletor.addEventListener("change", carregar);
carregar();
