from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    message: str = "Success"
    code: int = 200


def success_response(data: Any = None, message: str = "Success", code: int = 200) -> ApiResponse[Any]:
    return ApiResponse(success=True, data=data, message=message, code=code)


def error_response(message: str, code: int = 400, data: Any = None) -> ApiResponse[Any]:
    return ApiResponse(success=False, data=data, message=message, code=code)
