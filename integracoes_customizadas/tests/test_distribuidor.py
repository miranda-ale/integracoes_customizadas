import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe

from integracoes_customizadas.whatsapp import distribuidor

if not getattr(frappe.local, "flags", None):
	frappe.local.flags = frappe._dict(in_test=True)


def config(extras=()):
	linhas = [frappe._dict(instance_name=n, ativo=a, peso=p, limite_diario=l) for n, a, p, l in extras]
	return SimpleNamespace(instance_name="principal", instancias=linhas)


class FakeCache:
	def __init__(self):
		self.dados = {}

	def get_value(self, chave, generator=None, **_):
		if chave not in self.dados and generator:
			return generator()
		return self.dados.get(chave)

	def hget(self, *_, **__):  # tradução (`_()`) e fuso consultam o mesmo cache
		return {}

	def set_value(self, chave, valor, **_):
		self.dados[chave] = valor


class TestDistribuidor(unittest.TestCase):
	def setUp(self):
		self.cfg = config()
		self.cache = FakeCache()
		self.conectadas = {"principal", "segunda"}
		for alvo in (
			patch("integracoes_customizadas.whatsapp.api.get_settings", side_effect=lambda: self.cfg),
			patch.object(distribuidor.frappe, "cache", self.cache),
			patch.object(distribuidor, "today", return_value="2026-10-20"),
		):
			alvo.start()
			self.addCleanup(alvo.stop)

	def escolher(self, numero="5511999991234", **kw):
		return distribuidor.escolher_instancia(numero, estado=lambda nome: nome in self.conectadas, **kw)

	def test_instancia_unica_nao_consulta_estado(self):
		estado = MagicMock()
		self.assertEqual(distribuidor.escolher_instancia("5511999991234", estado=estado), "principal")
		estado.assert_not_called()

	def test_ignora_adicional_inativa_ou_duplicada(self):
		self.cfg = config([("segunda", 0, 1, 0), ("principal", 1, 1, 0)])
		self.assertEqual(distribuidor.nomes(self.cfg), ["principal"])

	def test_distribui_por_menor_carga(self):
		self.cfg = config([("segunda", 1, 1, 0)])
		escolhidas = [self.escolher(f"55119999912{i:02d}") for i in range(4)]
		self.assertEqual(sorted(escolhidas), ["principal", "principal", "segunda", "segunda"])

	def test_peso_dobra_a_participacao(self):
		self.cfg = config([("segunda", 1, 2, 0)])
		escolhidas = [self.escolher(f"55119999912{i:02d}") for i in range(6)]
		self.assertEqual(escolhidas.count("segunda"), 4)

	def test_afinidade_mantem_o_destinatario(self):
		self.cfg = config([("segunda", 1, 1, 0)])
		primeira = self.escolher("5511999991234")
		for _i in range(3):
			self.escolher("5511988887777")  # gera carga em outros números
		self.assertEqual(self.escolher("5511999991234"), primeira)

	def test_failover_quando_desconectada(self):
		self.cfg = config([("segunda", 1, 1, 0)])
		self.conectadas = {"segunda"}
		self.assertEqual(self.escolher(), "segunda")

	def test_limite_diario_desvia_para_outra(self):
		self.cfg = config([("segunda", 1, 1, 1)])
		self.assertEqual(self.escolher("5511999990001", preferida="segunda"), "segunda")
		self.assertEqual(self.escolher("5511999990002", preferida="segunda"), "principal")

	def test_sem_instancia_conectada(self):
		self.cfg = config([("segunda", 1, 1, 0)])
		self.conectadas = set()
		with self.assertRaises(distribuidor.SemInstanciaDisponivel):
			self.escolher()

	def test_excluir_instancia(self):
		self.cfg = config([("segunda", 1, 1, 0)])
		self.assertEqual(self.escolher(excluir=("principal",)), "segunda")


if __name__ == "__main__":
	unittest.main()
