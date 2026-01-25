from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar("T")



class APIResponse(BaseModel, Generic[T]):
    status_code: int
    message: str
    data: Optional[T] = None
    
def send_custom_response(status_code:int,message:str,data:Optional[T]=None):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
        },
        'body': APIResponse(status_code,message,data).model_dump_json()
    }