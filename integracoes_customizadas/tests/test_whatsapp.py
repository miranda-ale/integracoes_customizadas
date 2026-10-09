import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe

from integracoes_customizadas.whatsapp import api, delivery, notification

if not getattr(frappe.local, "flags", None):
	frappe.local.flags = frappe._dict(in_test=True)


class TestPhoneNumbers(unittest.TestCase):
	def test_brazil_and_international_numbers(self):
		self.assertEqual(delivery.normalize_phone("(11) 99999-1234"), "5511999991234")
		self.assertEqual(delivery.normalize_phone("55 11 99999-1234"), "5511999991234")
		self.assertEqual(delivery.normalize_phone("+1 (212) 555-1234"), "12125551234")

	def test_missing_and_invalid_numbers(self):
		for value in ("", "123", "11999991234 ramal 2", "55119999912345"):
			with self.subTest(value=value):
				self.assertIsNone(delivery.normalize_phone(value))


class TestRuleRecipients(unittest.TestCase):
	@patch.object(notification.frappe, "db", MagicMock())
	@patch.object(notification, "get_assignees", return_value=["assignee@example.com"])
	@patch.object(notification, "get_users", return_value=["role@example.com"])
	def test_role_owner_link_and_assignee(self, _roles, _assignees):
		notification.frappe.db.exists.return_value = True
		alert = SimpleNamespace(
			recipients=[
				SimpleNamespace(condition=None, receiver_by_role="Manager", receiver_by_document_field=None),
				SimpleNamespace(condition=None, receiver_by_role=None, receiver_by_document_field="owner"),
				SimpleNamespace(condition=None, receiver_by_role=None, receiver_by_document_field="responsavel"),
			],
			send_to_all_assignees=True,
		)
		doc = SimpleNamespace(owner="owner@example.com", get=lambda key: "linked@example.com")
		self.assertEqual(
			notification.recipient_users(alert, doc, {"doc": doc}),
			["assignee@example.com", "linked@example.com", "owner@example.com", "role@example.com"],
		)

	@patch.object(notification.frappe, "render_template", side_effect=lambda text, context: text)
	def test_message_uses_subject_and_readable_body(self, _render):
		alert = SimpleNamespace(subject="Aviso", notification_title=None, message="<p>Prazo <b>hoje</b></p>")
		self.assertEqual(notification.render_message(alert, {}), "Aviso\n\nPrazo\nhoje")

	@patch.object(notification.frappe, "db", MagicMock())
	@patch.object(notification.frappe, "get_doc")
	@patch.object(notification.frappe, "enqueue")
	@patch.object(notification, "recipient_users", return_value=["good@example.com", "bad@example.com"])
	@patch.object(notification, "render_message", return_value="Aviso\n\nMensagem")
	def test_queue_records_missing_phone_and_enqueues_valid_user(self, _render, _users, enqueue, get_doc):
		notification.frappe.db.get_value.side_effect = [
			SimpleNamespace(enabled=1, mobile_no="(11) 99999-1234"),
			SimpleNamespace(enabled=1, mobile_no=""),
		]
		records = []
		def create_record(values):
			records.append(values)
			return SimpleNamespace(name=f"delivery-{len(records)}", insert=lambda **kwargs: SimpleNamespace(name=f"delivery-{len(records)}"))
		get_doc.side_effect = create_record
		doc = SimpleNamespace(
			doctype="Task", name="TASK-1", parenttype=None, owner="owner@example.com",
			meta=SimpleNamespace(istable=False), get=lambda key: None,
		)
		alert = SimpleNamespace(name="Aviso tarefa")
		notification.queue_whatsapp(alert, doc)
		self.assertEqual([row["status"] for row in records], ["Pendente", "Ignorado"])
		self.assertEqual(records[0]["phone"], "5511999991234")
		enqueue.assert_called_once()
		self.assertTrue(enqueue.call_args.kwargs["enqueue_after_commit"])


class TestEvolutionAPI(unittest.TestCase):
	@patch.object(api, "require_manager")
	@patch.object(api, "get_settings", return_value=SimpleNamespace(instance_name="erp"))
	@patch.object(api, "evolution_request")
	def test_create_is_idempotent(self, request, _settings, _manager):
		request.return_value = [{"name": "erp"}]
		self.assertEqual(api.create_instance()["created"], False)
		request.assert_called_once()

	@patch.object(api, "require_manager")
	@patch.object(api, "get_settings", return_value=SimpleNamespace(instance_name="erp"))
	@patch.object(api, "evolution_request", side_effect=[[], {"instance": {"instanceName": "erp"}}])
	def test_create_new_instance(self, request, _settings, _manager):
		self.assertEqual(api.create_instance()["created"], True)
		self.assertEqual(request.call_args.args[:2], ("POST", "instance/create"))
		self.assertEqual(request.call_args.kwargs["json"]["integration"], "WHATSAPP-BAILEYS")

	@patch.object(api, "require_manager")
	@patch.object(api, "get_settings", return_value=SimpleNamespace(instance_name="erp"))
	@patch.object(api, "evolution_request", return_value={"code": "qr-payload"})
	def test_qr_code_is_generated_from_code(self, _request, _settings, _manager):
		result = api.get_qr_code()
		self.assertEqual(result["state"], "connecting")
		self.assertTrue(result["image"].startswith("data:image/svg+xml;base64,"))

	@patch.object(api, "require_manager")
	@patch.object(api.frappe, "get_doc")
	@patch.object(api.frappe, "enqueue")
	def test_retry_only_failed_delivery(self, enqueue, get_doc, _manager):
		entry = SimpleNamespace(name="delivery-1", status="Falhou")
		entry.db_set = MagicMock(side_effect=lambda values: setattr(entry, "status", values["status"]))
		get_doc.return_value = entry
		self.assertEqual(api.retry_delivery("delivery-1"), {"status": "Pendente"})
		self.assertEqual(entry.status, "Pendente")
		enqueue.assert_called_once()


class TestDelivery(unittest.TestCase):
	def make_delivery(self):
		item = SimpleNamespace(status="Pendente", attempts=0, phone="5511999991234", message="Olá", error=None)
		def db_set(key, value=None):
			for field, content in (key if isinstance(key, dict) else {key: value}).items():
				setattr(item, field, content)
		item.db_set = db_set
		return item

	@patch.object(delivery.frappe, "get_doc")
	@patch.object(delivery, "evolution_request", side_effect=[{"instance": {"state": "open"}}, {"key": {"id": "abc"}}])
	@patch.object(delivery, "instance_path", return_value="instance/connectionState/erp")
	@patch.object(delivery, "message_path", return_value="message/sendText/erp")
	@patch.object(delivery, "now_datetime", return_value="2026-10-09 12:00:00")
	def test_success(self, _now, _message_path, _instance_path, request, get_doc):
		item = self.make_delivery()
		get_doc.return_value = item
		delivery.send_delivery("entry")
		self.assertEqual(item.status, "Enviado")
		self.assertEqual(item.attempts, 1)
		self.assertEqual(item.provider_message_id, "abc")
		self.assertEqual(request.call_args.kwargs["json"], {"number": item.phone, "text": item.message})

	@patch.object(delivery.frappe, "get_doc")
	@patch.object(delivery, "evolution_request", return_value={"instance": {"state": "close"}})
	@patch.object(delivery, "instance_path", return_value="instance/connectionState/erp")
	def test_disconnected_is_recorded(self, _instance_path, request, get_doc):
		item = self.make_delivery()
		get_doc.return_value = item
		delivery.send_delivery("entry")
		self.assertEqual(item.status, "Falhou")
		self.assertIn("desconectada", item.error)
		request.assert_called_once()

	@patch.object(delivery.frappe, "get_doc")
	@patch.object(delivery, "evolution_request", side_effect=ValueError("Evolution API respondeu com HTTP 503."))
	@patch.object(delivery, "instance_path", return_value="instance/connectionState/erp")
	def test_provider_error_is_recorded_without_retry(self, _instance_path, request, get_doc):
		item = self.make_delivery()
		get_doc.return_value = item
		delivery.send_delivery("entry")
		self.assertEqual(item.status, "Falhou")
		self.assertIn("503", item.error)
		request.assert_called_once()


if __name__ == "__main__":
	unittest.main()
