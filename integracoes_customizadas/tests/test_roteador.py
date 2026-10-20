import frappe
from frappe.tests.utils import FrappeTestCase

from integracoes_customizadas.whatsapp import roteador


def _variantes(n):
	return [frappe._dict(name=f"v{i}", mensagem=f"m{i}", peso=1, ativo=1) for i in range(n)]


class TestRoteador(FrappeTestCase):
	def setUp(self):
		frappe.cache.delete_value(roteador._chave_global("t"))
		frappe.cache.delete_value(roteador._chave_destino("t", "5511999990000"))

	def test_sem_variantes_devolve_none(self):
		self.assertEqual(roteador.escolher([], chave="t"), (None, None))
		inativa = [frappe._dict(name="a", mensagem="x", ativo=0)]
		self.assertEqual(roteador.escolher(inativa, chave="t"), (None, None))

	def test_uma_variante_sempre_a_mesma(self):
		for _i in range(3):
			self.assertEqual(roteador.escolher(_variantes(1), chave="t")[1], "v0")

	def test_nao_repete_a_anterior(self):
		anterior = None
		for _i in range(40):
			_item, atual = roteador.escolher(_variantes(3), chave="t")
			self.assertNotEqual(atual, anterior)
			anterior = atual

	def test_nao_repete_ao_mesmo_destino(self):
		destino = "5511999990000"
		anterior = None
		for _i in range(40):
			_item, atual = roteador.escolher(_variantes(2), chave="t", destino=destino)
			self.assertNotEqual(atual, anterior)
			anterior = atual

	def test_peso_zero_ou_negativo_conta_como_um(self):
		variantes = _variantes(2)
		variantes[0].peso = 0
		self.assertIn(roteador.escolher(variantes, chave="t")[1], ("v0", "v1"))

	def test_sorteio_jinja(self):
		self.assertIn(roteador.sorteio("Oi", "Olá"), ("Oi", "Olá"))
		self.assertEqual(roteador.sorteio(), "")
