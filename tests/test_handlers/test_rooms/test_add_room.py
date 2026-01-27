import importlib
import json
import os
import unittest
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from src.common.models.users import UserRole
from src.common.models.rooms import Category


class AddRoomTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.env = patch.dict(os.environ, {"TABLE_NAME": "test-table"}, clear=False)
		cls.env.start()
		cls.resource = patch("src.handlers.rooms.add_room.resource")
		mock_res = cls.resource.start()
		mock_res.return_value.Table.return_value = MagicMock()
		import src.handlers.rooms.add_room as mod
		cls.mod = importlib.reload(mod)

	@classmethod
	def tearDownClass(cls):
		cls.resource.stop()
		cls.env.stop()

	def setUp(self):
		self.p_send = patch(
			"src.handlers.rooms.add_room.send_custom_response",
			side_effect=lambda status_code, message=None, data=None: {
				"statusCode": status_code,
				"body": json.dumps({"message": message, "data": data}),
			},
		)
		self.p_add = patch.object(self.mod.room_service, "add_room")
		self.mock_send = self.p_send.start()
		self.mock_add = self.p_add.start()

	def tearDown(self):
		self.p_send.stop()
		self.p_add.stop()

	def _event(self, role=UserRole.MANAGER.value, room_id="room1", category="deluxe", body=None):
		event = {
			"requestContext": {"authorizer": {"role": role}} if role is not None else {},
			"body": body if body is not None else json.dumps({"room_id": room_id, "category": category}),
		}
		return event

	def test_missing_authorizer_returns_401(self):
		resp = self.mod.add_room({"requestContext": {}}, None)
		self.assertEqual(401, resp["statusCode"])

	def test_invalid_role_value_returns_403(self):
		resp = self.mod.add_room(self._event(role="bad"), None)
		self.assertEqual(403, resp["statusCode"])

	def test_non_manager_admin_forbidden(self):
		resp = self.mod.add_room(self._event(role=UserRole.CUSTOMER.value), None)
		self.assertEqual(403, resp["statusCode"])

	def test_missing_body_returns_400(self):
		event = self._event()
		event["body"] = None
		resp = self.mod.add_room(event, None)
		self.assertEqual(400, resp["statusCode"])

	def test_invalid_json_body_returns_400(self):
		resp = self.mod.add_room(self._event(body="not-json"), None)
		self.assertEqual(400, resp["statusCode"])

	def test_missing_room_id_or_category_returns_400(self):
		resp = self.mod.add_room(self._event(body=json.dumps({"room_id": "room1"})), None)
		self.assertEqual(400, resp["statusCode"])
		resp2 = self.mod.add_room(self._event(body=json.dumps({"category": "deluxe"})), None)
		self.assertEqual(400, resp2["statusCode"])

	def test_invalid_category_returns_400(self):
		resp = self.mod.add_room(self._event(category="badcat"), None)
		self.assertEqual(400, resp["statusCode"])

	def test_duplicate_room_returns_400(self):
		ce = ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "TransactWriteItems")
		self.mock_add.side_effect = ce
		resp = self.mod.add_room(self._event(), None)
		self.assertEqual(400, resp["statusCode"])

	def test_client_error_returns_500(self):
		ce = ClientError({"Error": {"Code": "500", "Message": "fail"}}, "TransactWriteItems")
		self.mock_add.side_effect = ce
		resp = self.mod.add_room(self._event(), None)
		self.assertEqual(500, resp["statusCode"])

	def test_generic_error_returns_500(self):
		self.mock_add.side_effect = RuntimeError("boom")
		resp = self.mod.add_room(self._event(), None)
		self.assertEqual(500, resp["statusCode"])

	def test_success_adds_and_returns_201(self):
		resp = self.mod.add_room(self._event(), None)
		self.assertEqual(201, resp["statusCode"])
		self.mock_add.assert_called_once_with(room_id="room1", category=Category.DELUXE)


if __name__ == "__main__":
	unittest.main()
