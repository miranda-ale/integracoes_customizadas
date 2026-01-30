# Copyright (c) 2026
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, today

RISK_FIELDS = (
	"cj_probabilidade_perda",
	"cj_valor_estimado",
	"cj_provisao_atual",
	"cj_base_provisao",
)


def _normalize_cnj_digits(value: str) -> str:
	"""Return only digits from string, up to 20."""
	if not value:
		return ""
	return "".join(c for c in str(value) if c.isdigit())[:20]


class ProcessoJudicial(Document):
	def validate(self):
		self._normalizar_e_validar_numero_cnj()
		self._validar_eventos_idempotencia()
		self._atualizar_ultima_movimentacao()
		self._validar_regras_workflow()
		self._validar_prazos()

	def _normalizar_e_validar_numero_cnj(self):
		raw = _normalize_cnj_digits(self.cj_numero_cnj or "")
		if not raw:
			return
		if len(raw) != 20:
			frappe.throw(
				frappe._(
					"Número CNJ deve conter exatamente 20 dígitos (formato: NNNNNNN-DD.AAAA.J.TR.OOOO)."
				)
			)
		# Store normalized (20 digits only) for API compatibility
		self.cj_numero_cnj = raw

	def before_save(self):
		self._registrar_snapshot_risco_se_necessario()

	def _validar_eventos_idempotencia(self):
		ids = set()
		for evento in self.get("cj_eventos") or []:
			if not evento.cj_id_externo:
				continue
			if evento.cj_id_externo in ids:
				frappe.throw(
					frappe._(
						"Evento duplicado com cj_id_externo {0}."
					).format(evento.cj_id_externo)
				)
			ids.add(evento.cj_id_externo)

	def _atualizar_ultima_movimentacao(self):
		datas = [
			evento.cj_data_hora
			for evento in (self.get("cj_eventos") or [])
			if evento.cj_data_hora
		]
		if datas:
			self.cj_ultima_movimentacao_em = max(datas)

	def _registrar_snapshot_risco_se_necessario(self):
		before = self.get_doc_before_save()
		if not before:
			return

		alterou = any(
			getattr(before, field) != getattr(self, field)
			for field in RISK_FIELDS
		)
		if not alterou:
			return

		self.append(
			"cj_historico_risco",
			{
				"cj_data_hora_snapshot": now_datetime(),
				"cj_probabilidade_perda": self.cj_probabilidade_perda,
				"cj_valor_estimado": self.cj_valor_estimado,
				"cj_provisao": self.cj_provisao_atual,
				"cj_base": self.cj_base_provisao,
				"cj_usuario": frappe.session.user,
			},
		)

	def _validar_regras_workflow(self):
		estado = self.cj_estado_workflow
		if estado == "Encerrado":
			if not self.cj_resultado_final or not self.cj_data_encerramento:
				frappe.throw(
					frappe._(
						"Para encerrar o processo, preencha resultado final e data de encerramento."
					)
				)
			if not any(
				doc.cj_categoria in ["Sentença", "Acordo"]
				for doc in (self.get("cj_documentos") or [])
			):
				frappe.throw(
					frappe._(
						"Para encerrar o processo, é necessário anexar documento de categoria Sentença ou Acordo."
					)
				)

		if estado == "Arquivado":
			if self.cj_status != "Arquivado":
				frappe.throw(
					frappe._("Para arquivar, o status deve ser Arquivado.")
				)
			before = self.get_doc_before_save()
			if before and before.cj_estado_workflow != "Encerrado":
				frappe.throw(
					frappe._("Para arquivar, o processo deve estar Encerrado.")
				)

	def _validar_prazos(self):
		hoje = today()
		for prazo in self.get("cj_prazos") or []:
			if prazo.cj_status_prazo == "Cumprido" and not prazo.cj_concluido_em:
				prazo.cj_concluido_em = now_datetime()
			if (
				prazo.cj_status_prazo == "Cumprido"
				and not prazo.cj_observacao_conclusao
				and prazo.cj_data_vencimento
				and str(prazo.cj_data_vencimento) < str(hoje)
			):
				frappe.throw(
					frappe._(
						"Informe observação ao concluir prazo vencido."
					)
				)
