from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.grpc_gen import auth_pb2


class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime

    @classmethod
    def from_proto(cls, user: auth_pb2.User) -> "UserResponse":
        """Собирает ответ из proto-сообщения пользователя."""
        return cls(
            id=user.id,
            email=user.email,
            created_at=datetime.fromtimestamp(user.created_at, UTC),
        )
