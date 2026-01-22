import os
from src.common.repository.user_repo import UserRepository
from src.common.services.user_service import UserService
from src.common.schemas.users import  LoginRequest
from src.common.utils.custom_response import send_custom_response 

TABLE_NAME = os.environ.get('checkout_system_db')
repo = UserRepository(table_name=TABLE_NAME)
service = UserService(repo=repo) 

def signup(event,context):
    request_body=LoginRequest.model_validate_json(event["body"])
    try:
        token=service.login(request_body.email,request_body.password) 
        send_custom_response(status_code=200,message="login successful",data=token)
    except Exception as e:
        print(e)
    
    