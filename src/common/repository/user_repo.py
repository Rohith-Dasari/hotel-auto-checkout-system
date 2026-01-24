from botocore.exceptions import ClientError
import logging
from types_boto3_dynamodb.service_resource import Table
from types_boto3_dynamodb import DynamoDBClient
from typing import Optional
from boto3.dynamodb.conditions import Key
from src.common.models.users import User, UserRole

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, table: Table, client: DynamoDBClient = None):
        self.table = table
        self.client = client if client else table.meta.client

    def add_user(self, user: User):
        try:
            self.client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self.table.name,
                            "Item": {
                                "pk": f"EMAIL#{user.email}",
                                "sk": f"USER#{user.user_id}",
                            },
                            "ConditionExpression": "attribute_not_exists(pk)",
                        }
                    },
                    {
                        "Put": {
                            "TableName": self.table.name,
                            "Item": {
                                "pk": f"USER#{user.user_id}",
                                "sk": "DETAILS",
                                "username": user.username,
                                "email": user.email,
                                "phone_number": user.phone_number,
                                "password": user.password,
                                "role": user.role.value,
                            },
                            "ConditionExpression": "attribute_not_exists(pk)",
                        }
                    },
                ]
            )

        except ClientError as err:
            logger.error(
                "couldn't add user %s. Error: %s",
                user.email,
                err.response["Error"]["Message"],
            )
            raise

    def get_by_mail(self, mail: str) -> Optional[User]:
        try:
            response = self.table.query(
                KeyConditionExpression=(
                    Key("pk").eq(f"EMAIL#{mail}") & Key("sk").begins_with("USER#")
                )
            )
        except ClientError as err:
            logger.error(f"Error retrieving user by mail {mail}: {err}")
            raise

        items = response.get("Items", [])
        if not items:
            return None

        item = items[0]
        user_id = item["sk"].split("#", 1)[1]
        return self.get_by_id(user_id=user_id)

    def get_by_id(self, user_id: str) -> Optional[User]:
        try:
            response = self.table.get_item(
                Key={"pk": f"USER#{user_id}", "sk": "DETAILS"}
            )
        except ClientError as err:
            logger.error(f"Error retrieving user by id {user_id}: {err}")
            raise

        item = response.get("Item")
        if not item:
            return None

        return self._to_domain(item=item)

    @staticmethod
    def _to_domain(item: dict) -> User:
        return User(
            user_id=item["pk"].split("#", 1)[1],
            username=item["username"],
            email=item["email"],
            phone_number=item.get("phone_number"),
            role=UserRole(item["role"]),
            password=item["password"],
        )
