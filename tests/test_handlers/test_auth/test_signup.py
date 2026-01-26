import importlib, json, os, unittest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError
from pydantic import ValidationError
from src.common.utils.custom_exceptions import UserAlreadyExists

class SignupHandlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = patch.dict(os.environ, {"TABLE_NAME": "test-table"}, clear=False)
        cls.env.start()
        cls.resource = patch("src.handlers.auth.signup.resource")
        mock_resource = cls.resource.start()
        mock_resource.return_value.Table.return_value = MagicMock()
        import src.handlers.auth.signup as signup_module
        cls.mod = importlib.reload(signup_module)

    @classmethod
    def tearDownClass(cls):
        cls.resource.stop()
        cls.env.stop()

    def setUp(self):
        self.p_send = patch(
            "src.handlers.auth.signup.send_custom_response",
            side_effect=lambda status_code, message=None, data=None: {
                "statusCode": status_code,
                "body": json.dumps({"message": message, "data": data})
            },
        )
        self.p_validate = patch("src.handlers.auth.signup.SignupRequest.model_validate_json")
        self.p_signup = patch.object(self.mod.service, "signup")
        self.mock_send = self.p_send.start()
        self.mock_validate = self.p_validate.start()
        self.mock_signup = self.p_signup.start()

    def tearDown(self):
        self.p_send.stop()
        self.p_validate.stop()
        self.p_signup.stop()

    def _event(self):
        return {"body": json.dumps({
            "email": "u@test.com",
            "username": "u",
            "password": "Pw123456!",
            "phone_number": "9999999999"
        })}

    def test_success(self):
        req = MagicMock(email="u@test.com", username="u", password="Pw123456!", phone_number="9999999999")
        self.mock_validate.return_value = req
        self.mock_signup.return_value = {"token": "abc"}
        resp = self.mod.signup_handler(self._event(), None)
        self.assertEqual(201, resp["statusCode"])

    def test_validation_error(self):
        self.mock_validate.side_effect = ValidationError.from_exception_data("SignupRequest", [])
        resp = self.mod.signup_handler(self._event(), None)
        self.assertEqual(400, resp["statusCode"])

    def test_value_error(self):
        req = MagicMock(email="u@test.com", username="u", password="bad", phone_number="999")
        self.mock_validate.return_value = req
        self.mock_signup.side_effect = ValueError("bad input")
        resp = self.mod.signup_handler(self._event(), None)
        self.assertEqual(400, resp["statusCode"])

    def test_user_exists(self):
        req = MagicMock(email="u@test.com", username="u", password="Pw123456!", phone_number="9999999999")
        self.mock_validate.return_value = req
        self.mock_signup.side_effect = UserAlreadyExists("exists")
        resp = self.mod.signup_handler(self._event(), None)
        self.assertEqual(403, resp["statusCode"])

    def test_client_error(self):
        req = MagicMock(email="u@test.com", username="u", password="Pw123456!", phone_number="9999999999")
        self.mock_validate.return_value = req
        self.mock_signup.side_effect = ClientError({"Error": {"Code": "500", "Message": "fail"}}, "Signup")
        resp = self.mod.signup_handler(self._event(), None)
        self.assertEqual(500, resp["statusCode"])

    def test_generic_error(self):
        req = MagicMock(email="u@test.com", username="u", password="Pw123456!", phone_number="9999999999")
        self.mock_validate.return_value = req
        self.mock_signup.side_effect = RuntimeError("boom")
        resp = self.mod.signup_handler(self._event(), None)
        self.assertEqual(500, resp["statusCode"])

if __name__ == "__main__":
    unittest.main()