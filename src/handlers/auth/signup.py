import os
from src.common.repository.user_repo import UserRepository
from src.common.services.user_service import UserService
from src.common.schemas.users import SignupRequest
from src.common.utils.custom_response import send_custom_response
from boto3 import resource
from pydantic import ValidationError
from botocore.exceptions import ClientError


TABLE_NAME = os.environ.get("TABLE_NAME")
dynamodb = resource("dynamodb", region_name="ap-south-1")
table = dynamodb.Table(TABLE_NAME)

user_repo = UserRepository(table=table)
service = UserService(user_repo=user_repo)


def signup_handler(event, context):
    try:
        request_body = SignupRequest.model_validate_json(event["body"])
    except ValidationError as e:
        return send_custom_response(400, e.errors())
    
    try:
        token = service.signup(
            request_body.email,
            request_body.username,
            request_body.password,
            request_body.phone_number,
        )
        return send_custom_response(status_code=201, message="signup successful", data=token)
    except ClientError as e:
        return send_custom_response(status_code=500,message=str(e))
    except Exception as e:
            print(e)
            return send_custom_response(status_code=500, message="Internal server error")
