from typing import Optional
from src.common.models.users import User, UserRole
from src.common.repository.user_repo import UserRepository
from src.common.utils.custom_exceptions import (
    IncorrectCredentials,
    UserAlreadyExists,
    NotFoundException,
)
import bcrypt
import re
import uuid
from src.common.utils.jwt_service import create_jwt

PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{12,}$")


class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def get_user_by_id(self, user_id: str):
        user = self.user_repo.get_by_id(user_id=user_id)
        if user is None:
            raise NotFoundException(
                resource="user", identifier=user_id, status_code=404
            )
        return user

    def get_user_by_mail(self, mail):
        user = self.user_repo.get_by_mail(mail=mail)
        if user is None:
            raise NotFoundException(resource="user", identifier=mail, status_code=404)
        return user

    def login(self, email: str, password: str) -> str:
        user = self.get_user_by_mail(email)

        if not bcrypt.checkpw(
            password.encode("utf-8"),
            user.password.encode("utf-8"),
        ):
            raise IncorrectCredentials("Invalid email or password")

        return create_jwt(user.user_id, email, user.role.value)

    def signup(self, email: str, username: str, password: str, phone: str) -> str:
        self._is_email_valid(email)
        self._is_password_valid(password)
        self._is_number_valid(phone)

        hashed = self._hash_password(password)
        user_id = str(uuid.uuid4())

        self.user_repo.add_user(
            User(
                user_id=user_id,
                username=username,
                email=email,
                phone_number=phone,
                password=hashed,
                role=UserRole.CUSTOMER,
            )
        )
        return create_jwt(user_id, email, UserRole.CUSTOMER.value)

    def _is_number_valid(self, phone: str):
        if not phone.isdigit() or len(phone) != 10:
            raise ValueError("Invalid phone number")

    def _is_password_valid(self, password: str):
        if not PASSWORD_REGEX.fullmatch(password):
            raise ValueError(
                "Password must be at least 12 characters long and contain "
                "uppercase, lowercase, digit, and special character"
            )

    def _hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def _is_email_valid(self, email: str):
        pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(pattern, email):
            raise ValueError("Invalid email format")
        user = self.user_repo.get_by_mail(mail=email)
        if user:
            raise UserAlreadyExists("email is already in use")
