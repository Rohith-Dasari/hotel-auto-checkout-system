import unittest
from unittest.mock import MagicMock, patch
import bcrypt

from src.common.services.user_service import UserService
from src.common.models.users import User, UserRole
from src.common.utils.custom_exceptions import (
    IncorrectCredentials,
    UserAlreadyExists,
    NotFoundException,
)


class TestUserService(unittest.TestCase):

    def setUp(self):
        self.repo = MagicMock()
        self.service = UserService(self.repo)

        self.user = User(
            user_id="u1",
            username="rohith",
            email="test@example.com",
            phone_number="9876543210",
            password="hashed",
            role=UserRole.CUSTOMER,
        )
        
    def test_get_user_by_id_success(self):
        self.repo.get_by_id.return_value = self.user

        result = self.service.get_user_by_id("u1")

        self.repo.get_by_id.assert_called_once_with(user_id="u1")
        self.assertEqual(result, self.user)

    def test_get_user_by_id_not_found(self):
        self.repo.get_by_id.return_value = None

        with self.assertRaises(NotFoundException):
            self.service.get_user_by_id("missing")

 
    def test_get_user_by_mail_success(self):
        self.repo.get_by_mail.return_value = self.user

        result = self.service.get_user_by_mail("test@example.com")

        self.repo.get_by_mail.assert_called_once_with(mail="test@example.com")
        self.assertEqual(result, self.user)

    def test_get_user_by_mail_not_found(self):
        self.repo.get_by_mail.return_value = None

        with self.assertRaises(NotFoundException):
            self.service.get_user_by_mail("test@example.com")

    @patch("src.common.services.user_service.create_jwt")
    def test_login_success(self, mock_jwt):
        password = "StrongPass!123"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        self.user.password = hashed

        self.repo.get_by_mail.return_value = self.user
        mock_jwt.return_value = "fake-token"

        token = self.service.login("test@example.com", password)

        self.assertEqual(token, "fake-token")
        mock_jwt.assert_called_once_with(
            "u1",
            "test@example.com",
            UserRole.CUSTOMER.value
        )

    def test_login_wrong_password(self):
        self.user.password = bcrypt.hashpw(
            b"CorrectPass!123",
            bcrypt.gensalt()
        ).decode()

        self.repo.get_by_mail.return_value = self.user

        with self.assertRaises(IncorrectCredentials):
            self.service.login("test@example.com", "WrongPass!123")


    @patch("src.common.services.user_service.create_jwt")
    def test_signup_success(self, mock_jwt):
        self.repo.get_by_mail.return_value = None
        mock_jwt.return_value = "fake-token"

        token = self.service.signup(
            email="new@example.com",
            username="rohith",
            password="StrongPass!123",
            phone="9876543210"
        )

        self.repo.add_user.assert_called_once()
        self.assertEqual(token, "fake-token")

    def test_signup_invalid_email(self):
        with self.assertRaises(ValueError):
            self.service.signup(
                email="bad-email",
                username="rohith",
                password="StrongPass!123",
                phone="9876543210"
            )

    def test_signup_invalid_password(self):
        self.repo.get_by_mail.return_value = None

        with self.assertRaises(ValueError):
            self.service.signup(
                email="test@example.com",
                username="rohith",
                password="weak",
                phone="9876543210"
            )

    def test_signup_invalid_phone(self):
        self.repo.get_by_mail.return_value = None

        with self.assertRaises(ValueError):
            self.service.signup(
                email="test@example.com",
                username="rohith",
                password="StrongPass!123",
                phone="123"
            )

    def test_signup_duplicate_email(self):
        self.repo.get_by_mail.return_value = self.user

        with self.assertRaises(UserAlreadyExists):
            self.service.signup(
                email="test@example.com",
                username="rohith",
                password="StrongPass!123",
                phone="9876543210"
            )


if __name__ == "__main__":
    unittest.main()
