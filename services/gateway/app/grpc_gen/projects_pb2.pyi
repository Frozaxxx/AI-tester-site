from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Project(_message.Message):
    __slots__ = ("id", "name", "base_url", "created_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    BASE_URL_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    base_url: str
    created_at: int
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., base_url: _Optional[str] = ..., created_at: _Optional[int] = ...) -> None: ...

class Scenario(_message.Message):
    __slots__ = ("id", "project_id", "title", "text", "created_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    project_id: str
    title: str
    text: str
    created_at: int
    def __init__(self, id: _Optional[str] = ..., project_id: _Optional[str] = ..., title: _Optional[str] = ..., text: _Optional[str] = ..., created_at: _Optional[int] = ...) -> None: ...

class ProjectList(_message.Message):
    __slots__ = ("projects",)
    PROJECTS_FIELD_NUMBER: _ClassVar[int]
    projects: _containers.RepeatedCompositeFieldContainer[Project]
    def __init__(self, projects: _Optional[_Iterable[_Union[Project, _Mapping]]] = ...) -> None: ...

class ScenarioList(_message.Message):
    __slots__ = ("scenarios",)
    SCENARIOS_FIELD_NUMBER: _ClassVar[int]
    scenarios: _containers.RepeatedCompositeFieldContainer[Scenario]
    def __init__(self, scenarios: _Optional[_Iterable[_Union[Scenario, _Mapping]]] = ...) -> None: ...

class CreateProjectRequest(_message.Message):
    __slots__ = ("owner_id", "name", "base_url")
    OWNER_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    BASE_URL_FIELD_NUMBER: _ClassVar[int]
    owner_id: str
    name: str
    base_url: str
    def __init__(self, owner_id: _Optional[str] = ..., name: _Optional[str] = ..., base_url: _Optional[str] = ...) -> None: ...

class ListProjectsRequest(_message.Message):
    __slots__ = ("owner_id",)
    OWNER_ID_FIELD_NUMBER: _ClassVar[int]
    owner_id: str
    def __init__(self, owner_id: _Optional[str] = ...) -> None: ...

class ProjectRequest(_message.Message):
    __slots__ = ("owner_id", "project_id")
    OWNER_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    owner_id: str
    project_id: str
    def __init__(self, owner_id: _Optional[str] = ..., project_id: _Optional[str] = ...) -> None: ...

class CreateScenarioRequest(_message.Message):
    __slots__ = ("owner_id", "project_id", "title", "text")
    OWNER_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    owner_id: str
    project_id: str
    title: str
    text: str
    def __init__(self, owner_id: _Optional[str] = ..., project_id: _Optional[str] = ..., title: _Optional[str] = ..., text: _Optional[str] = ...) -> None: ...

class ScenarioRequest(_message.Message):
    __slots__ = ("owner_id", "scenario_id")
    OWNER_ID_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_ID_FIELD_NUMBER: _ClassVar[int]
    owner_id: str
    scenario_id: str
    def __init__(self, owner_id: _Optional[str] = ..., scenario_id: _Optional[str] = ...) -> None: ...
