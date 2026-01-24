import os
from src.common.repository.user_repo import UserRepository
from src.common.services.user_service import UserService
from src.common.schemas.users import  LoginRequest
from src.common.utils.custom_response import send_custom_response 
from pydantic import ValidationError

TABLE_NAME = os.environ.get('TABLE_NAME')
repo = UserRepository(table_name=TABLE_NAME)
service = UserService(repo=repo) 

def login_handler(event,context):
    try:
        request_body=LoginRequest.model_validate_json(event["body"])
    except ValidationError as e:
        return send_custom_response(400, e.errors())
    try:
        token=service.login(request_body.email,request_body.password) 
        send_custom_response(status_code=200,message="login successful",data=token)
    except Exception as e:
        print(e)
    
    