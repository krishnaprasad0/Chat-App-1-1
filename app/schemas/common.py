from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    status: bool = True
    message: str = ""
    data: Optional[T] = None
    errors: Optional[Any] = None
