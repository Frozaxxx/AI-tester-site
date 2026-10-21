import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.grpc_gen import auth_pb2, projects_pb2, runs_pb2


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


def _optional_datetime(message, field: str) -> datetime | None:
    """Возвращает дату из optional-поля proto или None, если поле не заполнено."""
    return _datetime(getattr(message, field)) if message.HasField(field) else None


def _optional(message, field: str):
    """Возвращает значение optional-поля proto или None, если поле не заполнено."""
    return getattr(message, field) if message.HasField(field) else None


class RunCreate(BaseModel):
    scenario_id: uuid.UUID | None = None


class RunResponse(BaseModel):
    id: str
    project_id: str
    scenario_id: str | None
    status: str
    tokens_used: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @classmethod
    def from_proto(cls, run: runs_pb2.Run) -> "RunResponse":
        """Собирает ответ из proto-сообщения прогона."""
        return cls(
            id=run.id,
            project_id=run.project_id,
            scenario_id=_optional(run, "scenario_id"),
            status=run.status,
            tokens_used=run.tokens_used,
            created_at=_datetime(run.created_at),
            started_at=_optional_datetime(run, "started_at"),
            finished_at=_optional_datetime(run, "finished_at"),
        )


class StepResponse(BaseModel):
    index: int
    action: str
    ok: bool
    locator: str | None
    value: str | None
    error: str | None

    @classmethod
    def from_proto(cls, step: runs_pb2.Step) -> "StepResponse":
        """Собирает ответ из proto-сообщения шага."""
        return cls(
            index=step.index,
            action=step.action,
            ok=step.ok,
            locator=_optional(step, "locator"),
            value=_optional(step, "value"),
            error=_optional(step, "error"),
        )


class FindingResponse(BaseModel):
    id: str
    kind: str
    title: str
    details: str
    step_index: int | None
    reproduced: bool

    @classmethod
    def from_proto(cls, finding: runs_pb2.Finding) -> "FindingResponse":
        """Собирает ответ из proto-сообщения бага."""
        return cls(
            id=finding.id,
            kind=finding.kind,
            title=finding.title,
            details=finding.details,
            step_index=_optional(finding, "step_index"),
            reproduced=finding.reproduced,
        )


class GeneratedTestResponse(BaseModel):
    code: str
    verified: bool


class RunDetailsResponse(BaseModel):
    run: RunResponse
    steps: list[StepResponse]
    findings: list[FindingResponse]
    test: GeneratedTestResponse | None

    @classmethod
    def from_proto(cls, details: runs_pb2.RunDetails) -> "RunDetailsResponse":
        """Собирает ответ с прогоном, шагами, багами и сгенерированным тестом."""
        test = None
        if details.HasField("test"):
            test = GeneratedTestResponse(code=details.test.code, verified=details.test.verified)
        return cls(
            run=RunResponse.from_proto(details.run),
            steps=[StepResponse.from_proto(step) for step in details.steps],
            findings=[FindingResponse.from_proto(finding) for finding in details.findings],
            test=test,
        )
