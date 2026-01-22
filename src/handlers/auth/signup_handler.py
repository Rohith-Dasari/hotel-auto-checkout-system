import os
from src.common.repository.user_repo import UserRepository
from src.common.services.user_service import UserService
from src.common.schemas.users import  SignupRequest
from src.common.utils.custom_response import send_custom_response 

TABLE_NAME = os.environ.get('checkout_system_db')
repo = UserRepository(table_name=TABLE_NAME)
service = UserService(repo=repo) 

def signup(event,context):
    request_body=SignupRequest.model_validate_json(event["body"])
    try:
        token=service.signup(request_body.email,request_body.username,request_body.password,request_body.phone_number) 
        send_custom_response(status_code=201,message="signup successful",data=token)
    except Exception as e:
        print(e)
    
