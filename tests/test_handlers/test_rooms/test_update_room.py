import importlib
import json
import os
import unittest
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from common.models.users import UserRole
from common.models.rooms import RoomStatus
from common.utils.custom_exceptions import NotFoundException


class UpdateRoomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = patch.dict(os.environ, {"TABLE_NAME": "test-table"}, clear=False)
        cls.env.start()
        cls.resource = patch("handlers.rooms.update_room.resource")
        mock_res = cls.resource.start()
        mock_res.return_value.Table.return_value = MagicMock()
        import handlers.rooms.update_room as mod
        cls.mod = importlib.reload(mod)

    @classmethod
    def tearDownClass(cls):
        cls.resource.stop()
        cls.env.stop()

    def setUp(self):
        self.p_send = patch(
            "handlers.rooms.update_room.send_custom_response",
            side_effect=lambda status_code, message=None, data=None: {
                "statusCode": status_code,
                "body": json.dumps({"message": message, "data": data}),
            },
        )
        self.p_update = patch.object(self.mod.room_service, "update_room_status")
        self.mock_send = self.p_send.start()
        self.mock_update = self.p_update.start()

    def tearDown(self):
        self.p_send.stop()
        self.p_update.stop()

    def _event(self, role=UserRole.MANAGER.value, room_id="room1", body=None):
        event = {
            "requestContext": {"authorizer": {"role": role}},
            "pathParameters": {"room_id": room_id} if room_id is not None else None,
            "body": body,
        }
        return event

    def test_missing_authorizer_returns_401(self):
        resp = self.mod.update_room({"requestContext": {}}, None)
        self.assertEqual(401, resp["statusCode"])

    def test_invalid_role_value_returns_403(self):
        resp = self.mod.update_room(self._event(role="bad"), None)
        self.assertEqual(403, resp["statusCode"])

    def test_non_manager_forbidden(self):
        resp = self.mod.update_room(self._event(role=UserRole.CUSTOMER.value), None)
        self.assertEqual(403, resp["statusCode"])

    def test_missing_room_id_returns_400(self):
        resp = self.mod.update_room(self._event(room_id=None), None)
        self.assertEqual(400, resp["statusCode"])

    def test_missing_body_returns_400(self):
        resp = self.mod.update_room(self._event(body=None), None)
        self.assertEqual(400, resp["statusCode"])

    def test_invalid_json_body_returns_400(self):
        resp = self.mod.update_room(self._event(body="not-json"), None)
        self.assertEqual(400, resp["statusCode"])

    def test_missing_status_returns_400(self):
        resp = self.mod.update_room(self._event(body=json.dumps({})), None)
        self.assertEqual(400, resp["statusCode"])

    def test_invalid_status_returns_400(self):
        resp = self.mod.update_room(self._event(body=json.dumps({"status": "bad"})), None)
        self.assertEqual(400, resp["statusCode"])

    def test_not_found_exception_returns_404(self):
        self.mock_update.side_effect = NotFoundException("room", "room1", 404)
        resp = self.mod.update_room(
            self._event(body=json.dumps({"status": RoomStatus.AVAILABLE.value})), None
        )
        self.assertEqual(404, resp["statusCode"])

    def test_client_error_returns_500(self):
        ce = ClientError({"Error": {"Code": "500", "Message": "fail"}}, "UpdateItem")
        self.mock_update.side_effect = ce
        resp = self.mod.update_room(
            self._event(body=json.dumps({"status": RoomStatus.AVAILABLE.value})), None
        )
        self.assertEqual(500, resp["statusCode"])

    def test_generic_error_returns_500(self):
        self.mock_update.side_effect = RuntimeError("boom")
        resp = self.mod.update_room(
            self._event(body=json.dumps({"status": RoomStatus.AVAILABLE.value})), None
        )
        self.assertEqual(500, resp["statusCode"])

    def test_success_updates_and_returns_200(self):
        resp = self.mod.update_room(
            self._event(body=json.dumps({"status": RoomStatus.HOUSEKEEPING.value})), None
        )
        self.assertEqual(200, resp["statusCode"])
        self.mock_update.assert_called_once_with(room_id="room1", status=RoomStatus.HOUSEKEEPING)
        body = json.loads(resp["body"])
        self.assertEqual("room1", body["data"]["room_id"])
        self.assertEqual(RoomStatus.HOUSEKEEPING.value, body["data"]["new_status"])


if __name__ == "__main__":
    unittest.main()
