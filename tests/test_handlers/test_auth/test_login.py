import importlib
import json
import os
import unittest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError
from pydantic import ValidationError

class LoginHandlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = patch.dict(os.environ, {"TABLE_NAME": "test-table"}, clear=False)
        cls.env.start()
        cls.resource = patch("src.handlers.auth.login.resource")
        mock_resource = cls.resource.start()
        mock_resource.return_value.Table.return_value = MagicMock()
        import src.handlers.auth.login as login_module
        cls.mod = importlib.reload(login_module)

    @classmethod
    def tearDownClass(cls):
        cls.resource.stop()
        cls.env.stop()

    def setUp(self):
        self.p_send = patch(
            "src.handlers.auth.login.send_custom_response",
            side_effect=lambda status_code, message=None, data=None: {
                "statusCode": status_code,
                "body": json.dumps({"message": message, "data": data})
            },
        )
        self.p_validate = patch("src.handlers.auth.login.LoginRequest.model_validate_json")
        self.p_login = patch.object(self.mod.service, "login")
        self.mock_send = self.p_send.start()
        self.mock_validate = self.p_validate.start()
        self.mock_login = self.p_login.start()

    def tearDown(self):
        self.p_send.stop()
        self.p_validate.stop()
        self.p_login.stop()

    def _event(self):
        return {"body": json.dumps({"email": "u@test.com", "password": "pw"})}

    def test_success(self):
        self.mock_validate.return_value.email = "u@test.com"
        self.mock_validate.return_value.password = "pw"
        self.mock_login.return_value = {"token": "abc"}
        resp = self.mod.login_handler(self._event(), None)
        self.assertEqual(200, resp["statusCode"])
        self.mock_login.assert_called_once_with("u@test.com", "pw")

    def test_validation_error(self):
        self.mock_validate.side_effect = ValidationError.from_exception_data("LoginRequest", [])
        resp = self.mod.login_handler(self._event(), None)
        self.assertEqual(400, resp["statusCode"])

    def test_incorrect_credentials(self):
        from src.common.utils.custom_exceptions import IncorrectCredentials
        self.mock_validate.return_value.email = "u@test.com"
        self.mock_validate.return_value.password = "pw"
        self.mock_login.side_effect = IncorrectCredentials("bad")
        resp = self.mod.login_handler(self._event(), None)
        self.assertEqual(401, resp["statusCode"])

    def test_not_found(self):
        from src.common.utils.custom_exceptions import NotFoundException
        self.mock_validate.return_value.email = "u@test.com"
        self.mock_validate.return_value.password = "pw"
        self.mock_login.side_effect = NotFoundException("user", "id", 404)
        resp = self.mod.login_handler(self._event(), None)
        self.assertEqual(404, resp["statusCode"])

    def test_client_error(self):
        ce = ClientError({"Error": {"Code": "500", "Message": "fail"}}, "Login")
        self.mock_validate.return_value.email = "u@test.com"
        self.mock_validate.return_value.password = "pw"
        self.mock_login.side_effect = ce
        resp = self.mod.login_handler(self._event(), None)
        self.assertEqual(500, resp["statusCode"])

    def test_generic_error(self):
        self.mock_validate.return_value.email = "u@test.com"
        self.mock_validate.return_value.password = "pw"
        self.mock_login.side_effect = RuntimeError("boom")
        resp = self.mod.login_handler(self._event(), None)
        self.assertEqual(500, resp["statusCode"])

if __name__ == "__main__":
    unittest.main()