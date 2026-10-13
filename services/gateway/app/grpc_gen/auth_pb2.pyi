from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Credentials(_message.Message):
    __slots__ = ("email", "password")
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    email: str
    password: str
    def __init__(self, email: _Optional[str] = ..., password: _Optional[str] = ...) -> None: ...

class User(_message.Message):
    __slots__ = ("id", "email", "created_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    email: str
    created_at: int
    def __init__(self, id: _Optional[str] = ..., email: _Optional[str] = ..., created_at: _Optional[int] = ...) -> None: ...

class TokenPair(_message.Message):
    __slots__ = ("user", "access_token", "access_expires_at", "refresh_token", "refresh_expires_at")
    USER_FIELD_NUMBER: _ClassVar[int]
    ACCESS_TOKEN_FIELD_NUMBER: _ClassVar[int]
    ACCESS_EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    REFRESH_TOKEN_FIELD_NUMBER: _ClassVar[int]
    REFRESH_EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    user: User
    access_token: str
    access_expires_at: int
    refresh_token: str
    refresh_expires_at: int
    def __init__(self, user: _Optional[_Union[User, _Mapping]] = ..., access_token: _Optional[str] = ..., access_expires_at: _Optional[int] = ..., refresh_token: _Optional[str] = ..., refresh_expires_at: _Optional[int] = ...) -> None: ...

class RefreshRequest(_message.Message):
    __slots__ = ("refresh_token",)
    REFRESH_TOKEN_FIELD_NUMBER: _ClassVar[int]
    refresh_token: str
    def __init__(self, refresh_token: _Optional[str] = ...) -> None: ...

class LogoutRequest(_message.Message):
    __slots__ = ("refresh_token", "access_token")
    REFRESH_TOKEN_FIELD_NUMBER: _ClassVar[int]
    ACCESS_TOKEN_FIELD_NUMBER: _ClassVar[int]
    refresh_token: str
    access_token: str
    def __init__(self, refresh_token: _Optional[str] = ..., access_token: _Optional[str] = ...) -> None: ...

class GetUserRequest(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class PublicKey(_message.Message):
    __slots__ = ("pem",)
    PEM_FIELD_NUMBER: _ClassVar[int]
    pem: str
    def __init__(self, pem: _Optional[str] = ...) -> None: ...
