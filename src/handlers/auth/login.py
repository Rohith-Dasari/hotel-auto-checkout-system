import os
from common.repository.user_repo import UserRepository
from common.services.user_service import UserService
from common.schemas.users import  LoginRequest
from common.utils.custom_exceptions import IncorrectCredentials,NotFoundException
from common.utils.custom_response import send_custom_response 
from pydantic import ValidationError
from botocore.exceptions import ClientError
from boto3 import resource

TABLE_NAME = os.environ.get('TABLE_NAME')
dynamodb = resource("dynamodb", region_name="ap-south-1")
table = dynamodb.Table(TABLE_NAME)
repo = UserRepository(table=table)
service = UserService(user_repo=repo) 

def login_handler(event,context):
    try:
        request_body=LoginRequest.model_validate_json(event["body"])
    except ValidationError as e:
        return send_custom_response(400, e.errors())
    try:
        token=service.login(request_body.email,request_body.password) 
        return send_custom_response(status_code=200,message="login successful",data=token)
    except ClientError as e:
        return send_custom_response(status_code=500,message=str(e))
    except IncorrectCredentials as e:
        return send_custom_response(status_code=401,message=str(e))
    except NotFoundException as e:
        return send_custom_response(status_code=404, message=str(e))
    except Exception as e:
        print(e)
        return send_custom_response(status_code=500, message="Internal server error")
    
    