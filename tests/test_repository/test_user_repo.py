import unittest
from unittest.mock import MagicMock
from botocore.exceptions import ClientError

from common.repository.user_repo import UserRepository
from common.models.users import User, UserRole


class TestUserRepository(unittest.TestCase):

    def setUp(self):
        self.table = MagicMock()
        self.client = MagicMock()

        self.table.meta.client = self.client

        self.repo = UserRepository(self.table, self.client)

        self.user = User(
            user_id="u1",
            username="rohith",
            email="test@example.com",
            phone_number="9876543210",
            password="hashed-password",
            role=UserRole.CUSTOMER,
        )

    def test_add_user_success(self):
        self.client.transact_write_items.return_value = {}

        self.repo.add_user(self.user)

        self.client.transact_write_items.assert_called_once()
        _, kwargs = self.client.transact_write_items.call_args

        items = kwargs["TransactItems"]

        email_put = items[0]["Put"]
        self.assertEqual(email_put["TableName"], self.table.name)
        self.assertEqual(email_put["Item"]["pk"], "EMAIL#test@example.com")
        self.assertEqual(email_put["Item"]["sk"], "USER#u1")

        user_put = items[1]["Put"]
        self.assertEqual(user_put["Item"]["pk"], "USER#u1")
        self.assertEqual(user_put["Item"]["sk"], "DETAILS")
        self.assertEqual(user_put["Item"]["email"], "test@example.com")
        self.assertEqual(user_put["Item"]["role"], UserRole.CUSTOMER.value)

    def test_add_user_client_error_raises(self):
        self.client.transact_write_items.side_effect = ClientError(
            error_response={"Error": {"Message": "Dynamo failure"}},
            operation_name="TransactWriteItems"
        )

        with self.assertRaises(ClientError):
            self.repo.add_user(self.user)

    def test_get_by_id_success(self):
        self.table.get_item.return_value = {
            "Item": {
                "pk": "USER#u1",
                "sk": "DETAILS",
                "username": "rohith",
                "email": "test@example.com",
                "phone_number": "9876543210",
                "password": "hashed-password",
                "role": "CUSTOMER",
            }
        }

        result = self.repo.get_by_id("u1")

        self.table.get_item.assert_called_once_with(
            Key={"pk": "USER#u1", "sk": "DETAILS"}
        )

        self.assertEqual(result.user_id, "u1")
        self.assertEqual(result.email, "test@example.com")
        self.assertEqual(result.role, UserRole.CUSTOMER)

    def test_get_by_id_not_found(self):
        self.table.get_item.return_value = {}

        result = self.repo.get_by_id("missing")

        self.assertIsNone(result)

    def test_get_by_id_client_error(self):
        self.table.get_item.side_effect = ClientError(
            error_response={"Error": {"Message": "Get failed"}},
            operation_name="GetItem"
        )

        with self.assertRaises(ClientError):
            self.repo.get_by_id("u1")

    def test_get_by_mail_success(self):
        self.table.query.return_value = {
            "Items": [
                {
                    "pk": "EMAIL#test@example.com",
                    "sk": "USER#u1",
                }
            ]
        }

        self.table.get_item.return_value = {
            "Item": {
                "pk": "USER#u1",
                "sk": "DETAILS",
                "username": "rohith",
                "email": "test@example.com",
                "phone_number": "9876543210",
                "password": "hashed-password",
                "role": "CUSTOMER",
            }
        }

        result = self.repo.get_by_mail("test@example.com")

        self.table.query.assert_called_once()
        self.assertEqual(result.user_id, "u1")
        self.assertEqual(result.email, "test@example.com")

    def test_get_by_mail_not_found(self):
        self.table.query.return_value = {"Items": []}

        result = self.repo.get_by_mail("missing@example.com")

        self.assertIsNone(result)

    def test_get_by_mail_client_error(self):
        self.table.query.side_effect = ClientError(
            error_response={"Error": {"Message": "Query failed"}},
            operation_name="Query"
        )

        with self.assertRaises(ClientError):
            self.repo.get_by_mail("test@example.com")

    def test_to_domain_mapping(self):
        item = {
            "pk": "USER#u99",
            "sk": "DETAILS",
            "username": "alice",
            "email": "alice@example.com",
            "phone_number": "9999999999",
            "password": "pw",
            "role": "CUSTOMER",
        }

        user = self.repo._to_domain(item)

        self.assertEqual(user.user_id, "u99")
        self.assertEqual(user.username, "alice")
        self.assertEqual(user.email, "alice@example.com")
        self.assertEqual(user.role, UserRole.CUSTOMER)


if __name__ == "__main__":
    unittest.main()
