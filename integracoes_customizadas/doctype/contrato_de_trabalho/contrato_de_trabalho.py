import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate


ALERTA_DIAS = [60, 30, 15, 7, 3, 1, 0]  # use no scheduler

def _norm(s: str) -> str:
    """Normaliza string para comparação (lower + sem acentos + trim)."""
    if not s:
        return ""
    s = (s or "").strip().lower()
    # remove acentos sem depender de libs externas
    mapa = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüç",
        "aaaaaeeeeiiiiooooouuuuc"
    )
    return s.translate(mapa)

# Conjuntos normalizados (para comparar com _norm)
TIPOS_INDETERMINADO = {_norm(x) for x in ["Prazo indeterminado", "Indeterminado", "Indeterminado (CLT)", "Prazo Indeterminado"]}
TIPOS_INTERMITENTE = {_norm(x) for x in ["Intermitente", "Contrato intermitente"]}
TIPOS_EXPERIENCIA = {_norm(x) for x in ["Experiência", "Experiencia", "Contrato de experiencia"]}
TIPOS_DETERMINADO = {_norm(x) for x in [
    "Prazo determinado",
    "Prazo determinado com cláusula assecuratória",
    "Prazo determinado com clausula assecuratoria",
    "Contrato por prazo determinado",
]}

class ContratoDeTrabalho(Document):

    def validate(self):
        self._validar_regras_basicas()
        self._calcular_proximo_vencimento()
        self._calcular_dias_para_vencimento()
        self._calcular_status_prazo()

    # opcional (recomendado se você quer rigidez ao submeter)
    # def before_submit(self):
    #     self._validar_regras_basicas()
    #     self._calcular_proximo_vencimento()
    #     self._calcular_dias_para_vencimento()
    #     self._calcular_status_prazo()

    def _tipo(self) -> str:
        return _norm(self.tipo_contrato)

    def _encerrado(self) -> bool:
        return bool(self.data_rescisao) or (self.status in ["Encerrado", "Cancelado"])

    def _validar_regras_basicas(self):
        t = self._tipo()

        if not self.data_admissao:
            frappe.throw("Preencha a Data de Admissão.")

        if t in TIPOS_INDETERMINADO:
            return

        if t in TIPOS_INTERMITENTE:
            return

        if t in TIPOS_EXPERIENCIA or t in TIPOS_DETERMINADO:
            if not self.data_fim_determinado:
                frappe.throw("Para este tipo de contrato, preencha o campo 'Fim do Determinado'.")

            adm = getdate(self.data_admissao)
            fim1 = getdate(self.data_fim_determinado) if self.data_fim_determinado else None
            fim2 = getdate(self.data_fim_prorrogacao) if self.data_fim_prorrogacao else None

            if fim1 and fim1 < adm:
                frappe.throw("'Fim do Determinado' não pode ser anterior à Data de Admissão.")

            if fim2 and fim1 and fim2 < fim1:
                frappe.throw("'Fim da Prorrogação' não pode ser anterior ao 'Fim do Determinado'.")

            if self.data_rescisao:
                resc = getdate(self.data_rescisao)
                if resc < adm:
                    frappe.throw("'Data da Rescisão' não pode ser anterior à Data de Admissão.")

    def _calcular_proximo_vencimento(self):
        """
        Próximo vencimento:
        - Se houver fim_prorrogacao: ele é o vencimento final.
        - Caso contrário: fim_determinado.
        - Se quiser "próximo vencimento ainda não ocorrido", prioriza a data >= hoje.
        """
        if self._encerrado():
            self.proximo_vencimento = None
            return

        t = self._tipo()
        if t in TIPOS_INDETERMINADO or t in TIPOS_INTERMITENTE:
            self.proximo_vencimento = None
            return

        hoje = getdate(nowdate())
        fim1 = getdate(self.data_fim_determinado) if self.data_fim_determinado else None
        fim2 = getdate(self.data_fim_prorrogacao) if self.data_fim_prorrogacao else None

        # regra "inteligente": escolhe o próximo marco futuro; se ambos passaram, fica no último (fim2 > fim1)
        candidato = None
        if fim1 and fim1 >= hoje:
            candidato = fim1
        if fim2 and fim2 >= hoje:
            # se existe fim2 futuro, ele prevalece como "próximo" (vencimento final/prorrogação)
            candidato = fim2

        # se nenhum está no futuro, registra o último existente (para marcar vencido)
        if not candidato:
            candidato = fim2 or fim1

        self.proximo_vencimento = candidato

    def _calcular_dias_para_vencimento(self):
        if not self.proximo_vencimento:
            self.dias_para_vencimento = None
            return

        dias = frappe.datetime.get_day_diff(getdate(self.proximo_vencimento), getdate(nowdate()))
        self.dias_para_vencimento = int(dias)

    def _calcular_status_prazo(self):
        if self._encerrado():
            self.status_prazo = "Encerrado"
            return

        t = self._tipo()
        if t in TIPOS_INDETERMINADO or t in TIPOS_INTERMITENTE:
            self.status_prazo = "Não aplicável"
            return

        if self.dias_para_vencimento is None:
            self.status_prazo = "Não aplicável"
            return

        if self.dias_para_vencimento < 0:
            self.status_prazo = "Vencido"
        elif self.dias_para_vencimento <= 30:
            self.status_prazo = "A vencer"
        else:
            self.status_prazo = "Em dia"
