import importlib
import os
import unittest
from unittest.mock import patch, MagicMock
import jwt

class JwtAuthorizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = patch.dict(os.environ, {"JWT_SECRET": "testsecret", "JWT_ALGORITHM": "HS256"}, clear=False)
        cls.env.start()
        import handlers.auth.jwt_authorizer as mod
        cls.mod = importlib.reload(mod)

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()

    def setUp(self):
        self.p_decode = patch("handlers.auth.jwt_authorizer.jwt.decode")
        self.mock_decode = self.p_decode.start()

    def tearDown(self):
        self.p_decode.stop()

    def _event(self, token=None, method_arn="arn:aws:execute-api:123/test/GET/resource", headers=None, http_method=None):
        event = {"methodArn": method_arn}
        if token:
            event["authorizationToken"] = token
        if headers:
            event["headers"] = headers
        if http_method:
            event["httpMethod"] = http_method
        return event

    def test_missing_token_denies(self):
        event = self._event()
        resp = self.mod.lambda_handler(event, None)
        self.assertEqual("Deny", resp["policyDocument"]["Statement"][0]["Effect"])
        self.assertEqual("unauthorized", resp["principalId"])


    def test_token_in_authorizationToken(self):
        self.mock_decode.return_value = {"user_id": "u2", "email": "x@test.com", "role": "ADMIN"}
        event = self._event(token="Bearer testtoken")
        resp = self.mod.lambda_handler(event, None)
        self.assertEqual("Allow", resp["policyDocument"]["Statement"][0]["Effect"])
        self.assertEqual("u2", resp["principalId"])
        self.assertEqual("ADMIN", resp["context"]["role"])

    def test_token_missing_user_id_denies(self):
        self.mock_decode.return_value = {"email": "e@test.com", "role": "MANAGER"}
        event = self._event(token="Bearer testtoken")
        resp = self.mod.lambda_handler(event, None)
        self.assertEqual("Deny", resp["policyDocument"]["Statement"][0]["Effect"])
        self.assertEqual("unauthorized", resp["principalId"])

    def test_expired_signature_denies(self):
        self.mock_decode.side_effect = jwt.ExpiredSignatureError()
        event = self._event(token="Bearer testtoken")
        resp = self.mod.lambda_handler(event, None)
        self.assertEqual("Deny", resp["policyDocument"]["Statement"][0]["Effect"])
        self.assertEqual("unauthorized", resp["principalId"])

    def test_invalid_token_denies(self):
        self.mock_decode.side_effect = jwt.InvalidTokenError()
        event = self._event(token="Bearer testtoken")
        resp = self.mod.lambda_handler(event, None)
        self.assertEqual("Deny", resp["policyDocument"]["Statement"][0]["Effect"])
        self.assertEqual("unauthorized", resp["principalId"])

    def test_generic_exception_denies(self):
        self.mock_decode.side_effect = Exception("fail")
        event = self._event(token="Bearer testtoken")
        resp = self.mod.lambda_handler(event, None)
        self.assertEqual("Deny", resp["policyDocument"]["Statement"][0]["Effect"])
        self.assertEqual("unauthorized", resp["principalId"])

if __name__ == "__main__":
    unittest.main()
