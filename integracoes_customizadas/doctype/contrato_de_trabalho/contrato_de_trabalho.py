# apps/integracoes_customizadas/integracoes_customizadas/doctype/contrato_de_trabalho/contrato_de_trabalho.py

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

# ==============================
# Tipos (ajuste conforme seus valores reais em doc.tipo_contrato)
# ==============================
TIPOS_INDETERMINADO = {"Prazo indeterminado", "Indeterminado"}
TIPOS_INTERMITENTE = {"Intermitente"}
TIPOS_EXPERIENCIA = {"Experiência", "Experiencia"}
TIPOS_DETERMINADO = {
    "Prazo determinado",
    "Prazo determinado com cláusula assecuratória",
    "Prazo determinado com clausula assecuratoria",
}

# Se vocês utilizam "PJ" dentro do mesmo DocType, trate como NÃO aplicável a vencimentos CLT.
TIPOS_NAO_APLICAVEL = {"PJ", "Pessoa Jurídica", "Pessoa Juridica"}

# Política de alertas (se você for usar em Notification/Job)
ALERTA_DIAS = [60, 30, 15, 7, 3, 1, 0]


class ContratoDeTrabalho(Document):
    """
    DocType Controller - Contrato de Trabalho

    Campos esperados no DocType (fieldname):
      - tipo_contrato (Data/Select)  [já existe via fetch do Employee]
      - data_admissao (Date)         [fetch do employee.date_of_joining]
      - data_fim_determinado (Date)
      - data_fim_prorrogacao (Date)
      - data_rescisao (Date)
      - status (Select)             [Rascunho/Impresso/Assinado/Vigente/Encerrado/Cancelado]

    Campos de controle (devem existir no DocType):
      - proximo_vencimento (Date, Read Only)
      - dias_para_vencimento (Int, Read Only)
      - status_prazo (Select, Read Only) [Em dia / A vencer / Vencido / Encerrado / Não aplicável]
    """

    def validate(self):
        self._validar_regras_basicas()
        self._calcular_proximo_vencimento()
        self._calcular_dias_para_vencimento()
        self._calcular_status_prazo()

    # ------------------------------
    # Helpers
    # ------------------------------
    def _tipo(self) -> str:
        return (self.tipo_contrato or "").strip()

    def _encerrado(self) -> bool:
        # Encerrado se houver data_rescisao ou status final
        return bool(self.data_rescisao) or (self.status in {"Encerrado", "Cancelado"})

    def _nao_aplicavel(self) -> bool:
        t = self._tipo()
        return t in TIPOS_INDETERMINADO or t in TIPOS_INTERMITENTE or t in TIPOS_NAO_APLICAVEL

    # ------------------------------
    # Regras e Validações
    # ------------------------------
    def _validar_regras_basicas(self):
        t = self._tipo()

        if not self.data_admissao:
            frappe.throw("Preencha a Data de Admissão.")

        # Se for encerrado, ainda validamos coerência mínima com admissão.
        adm = getdate(self.data_admissao)

        if self.data_rescisao:
            resc = getdate(self.data_rescisao)
            if resc < adm:
                frappe.throw("'Data da Rescisão' não pode ser anterior à Data de Admissão.")

        # Tipos sem vencimento por data (CLT indeterminado / intermitente / PJ etc.)
        if t in TIPOS_INDETERMINADO or t in TIPOS_INTERMITENTE or t in TIPOS_NAO_APLICAVEL:
            return

        # Experiência / determinado: pelo menos fim_determinado deve existir
        if t in TIPOS_EXPERIENCIA or t in TIPOS_DETERMINADO:
            if not self.data_fim_determinado:
                frappe.throw("Para este tipo de contrato, preencha o campo 'Fim do Determinado'.")

            fim1 = getdate(self.data_fim_determinado) if self.data_fim_determinado else None
            fim2 = getdate(self.data_fim_prorrogacao) if self.data_fim_prorrogacao else None

            if fim1 and fim1 < adm:
                frappe.throw("'Fim do Determinado' não pode ser anterior à Data de Admissão.")

            if fim2 and fim1 and fim2 < fim1:
                frappe.throw("'Fim da Prorrogação' não pode ser anterior ao 'Fim do Determinado'.")

        # Se o tipo não for reconhecido, marque como não aplicável (evita “limbo”)
        else:
            # Não bloqueia salvamento, mas padroniza o comportamento.
            # Se preferir exigir padronização, troque para frappe.throw(...)
            self.status_prazo = "Não aplicável"
            self.proximo_vencimento = None
            self.dias_para_vencimento = None

    # ------------------------------
    # Cálculos de controle
    # ------------------------------
    def _calcular_proximo_vencimento(self):
        """
        Próximo vencimento:
          - Se encerrado: None
          - Se não aplicável (indeterminado/intermitente/PJ): None
          - Caso contrário: fim_prorrogacao (se existir) senão fim_determinado
        """
        # Garanta que os campos existem no DocType:
        # proximo_vencimento (Date)
        if self._encerrado():
            self.proximo_vencimento = None
            return

        if self._nao_aplicavel():
            self.proximo_vencimento = None
            return

        fim1 = getdate(self.data_fim_determinado) if self.data_fim_determinado else None
        fim2 = getdate(self.data_fim_prorrogacao) if self.data_fim_prorrogacao else None

        self.proximo_vencimento = fim2 or fim1

    def _calcular_dias_para_vencimento(self):
        """
        dias_para_vencimento:
          - None se não houver proximo_vencimento
          - Inteiro baseado em get_day_diff(vencimento, hoje)
        """
        # Garanta que o campo existe no DocType:
        # dias_para_vencimento (Int)
        if not getattr(self, "proximo_vencimento", None):
            self.dias_para_vencimento = None
            return

        hoje = getdate(nowdate())
        venc = getdate(self.proximo_vencimento)

        # get_day_diff: evita o erro clássico 'function object has no attribute get_day_diff'
        dias = frappe.datetime.get_day_diff(venc, hoje)
        self.dias_para_vencimento = int(dias)

    def _calcular_status_prazo(self):
        """
        status_prazo:
          - Encerrado se _encerrado()
          - Não aplicável se indeterminado/intermitente/PJ ou sem proximo_vencimento
          - Vencido se dias < 0
          - A vencer se 0 <= dias <= 30
          - Em dia se dias > 30
        """
        # Garanta que o campo existe no DocType:
        # status_prazo (Select)
        if self._encerrado():
            self.status_prazo = "Encerrado"
            return

        if self._nao_aplicavel():
            self.status_prazo = "Não aplicável"
            self.dias_para_vencimento = None  # mantém coerência
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
