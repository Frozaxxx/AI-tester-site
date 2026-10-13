from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.grpc_gen import auth_pb2, projects_pb2


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
            created_at=_datetime(user.created_at),
        )


def _datetime(timestamp: int) -> datetime:
    """Превращает unix-время из proto в дату с часовым поясом UTC."""
    return datetime.fromtimestamp(timestamp, UTC)


class ProjectCreate(BaseModel):
    name: str = Field(max_length=200)
    base_url: str = Field(max_length=2048)


class ProjectResponse(BaseModel):
    id: str
    name: str
    base_url: str
    created_at: datetime

    @classmethod
    def from_proto(cls, project: projects_pb2.Project) -> "ProjectResponse":
        """Собирает ответ из proto-сообщения проекта."""
        return cls(
            id=project.id,
            name=project.name,
            base_url=project.base_url,
            created_at=_datetime(project.created_at),
        )


class ScenarioCreate(BaseModel):
    title: str = Field(max_length=200)
    text: str = Field(max_length=10_000)


class ScenarioResponse(BaseModel):
    id: str
    project_id: str
    title: str
    text: str
    created_at: datetime

    @classmethod
    def from_proto(cls, scenario: projects_pb2.Scenario) -> "ScenarioResponse":
        """Собирает ответ из proto-сообщения сценария."""
        return cls(
            id=scenario.id,
            project_id=scenario.project_id,
            title=scenario.title,
            text=scenario.text,
            created_at=_datetime(scenario.created_at),
        )
