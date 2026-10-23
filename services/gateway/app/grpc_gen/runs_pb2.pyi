from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ClaimedRun(_message.Message):
    __slots__ = ("run", "owner_id")
    RUN_FIELD_NUMBER: _ClassVar[int]
    OWNER_ID_FIELD_NUMBER: _ClassVar[int]
    run: Run
    owner_id: str
    def __init__(self, run: _Optional[_Union[Run, _Mapping]] = ..., owner_id: _Optional[str] = ...) -> None: ...

class Run(_message.Message):
    __slots__ = ("id", "project_id", "scenario_id", "status", "tokens_used", "created_at", "started_at", "finished_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    TOKENS_USED_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    STARTED_AT_FIELD_NUMBER: _ClassVar[int]
    FINISHED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    project_id: str
    scenario_id: str
    status: str
    tokens_used: int
    created_at: int
    started_at: int
    finished_at: int
    def __init__(self, id: _Optional[str] = ..., project_id: _Optional[str] = ..., scenario_id: _Optional[str] = ..., status: _Optional[str] = ..., tokens_used: _Optional[int] = ..., created_at: _Optional[int] = ..., started_at: _Optional[int] = ..., finished_at: _Optional[int] = ...) -> None: ...

class Step(_message.Message):
    __slots__ = ("index", "action", "ok", "locator", "value", "error", "created_at")
    INDEX_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    OK_FIELD_NUMBER: _ClassVar[int]
    LOCATOR_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    index: int
    action: str
    ok: bool
    locator: str
    value: str
    error: str
    created_at: int
    def __init__(self, index: _Optional[int] = ..., action: _Optional[str] = ..., ok: _Optional[bool] = ..., locator: _Optional[str] = ..., value: _Optional[str] = ..., error: _Optional[str] = ..., created_at: _Optional[int] = ...) -> None: ...

class Finding(_message.Message):
    __slots__ = ("id", "kind", "title", "details", "step_index", "reproduced", "created_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    STEP_INDEX_FIELD_NUMBER: _ClassVar[int]
    REPRODUCED_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    kind: str
    title: str
    details: str
    step_index: int
    reproduced: bool
    created_at: int
    def __init__(self, id: _Optional[str] = ..., kind: _Optional[str] = ..., title: _Optional[str] = ..., details: _Optional[str] = ..., step_index: _Optional[int] = ..., reproduced: _Optional[bool] = ..., created_at: _Optional[int] = ...) -> None: ...

class GeneratedTest(_message.Message):
    __slots__ = ("code", "verified", "created_at")
    CODE_FIELD_NUMBER: _ClassVar[int]
    VERIFIED_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    code: str
    verified: bool
    created_at: int
    def __init__(self, code: _Optional[str] = ..., verified: _Optional[bool] = ..., created_at: _Optional[int] = ...) -> None: ...

class RunList(_message.Message):
    __slots__ = ("runs",)
    RUNS_FIELD_NUMBER: _ClassVar[int]
    runs: _containers.RepeatedCompositeFieldContainer[Run]
    def __init__(self, runs: _Optional[_Iterable[_Union[Run, _Mapping]]] = ...) -> None: ...

class RunDetails(_message.Message):
    __slots__ = ("run", "steps", "findings", "test")
    RUN_FIELD_NUMBER: _ClassVar[int]
    STEPS_FIELD_NUMBER: _ClassVar[int]
    FINDINGS_FIELD_NUMBER: _ClassVar[int]
    TEST_FIELD_NUMBER: _ClassVar[int]
    run: Run
    steps: _containers.RepeatedCompositeFieldContainer[Step]
    findings: _containers.RepeatedCompositeFieldContainer[Finding]
    test: GeneratedTest
    def __init__(self, run: _Optional[_Union[Run, _Mapping]] = ..., steps: _Optional[_Iterable[_Union[Step, _Mapping]]] = ..., findings: _Optional[_Iterable[_Union[Finding, _Mapping]]] = ..., test: _Optional[_Union[GeneratedTest, _Mapping]] = ...) -> None: ...

class CreateRunRequest(_message.Message):
    __slots__ = ("owner_id", "project_id", "scenario_id")
    OWNER_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_ID_FIELD_NUMBER: _ClassVar[int]
    owner_id: str
    project_id: str
    scenario_id: str
    def __init__(self, owner_id: _Optional[str] = ..., project_id: _Optional[str] = ..., scenario_id: _Optional[str] = ...) -> None: ...

class ListRunsRequest(_message.Message):
    __slots__ = ("owner_id", "project_id")
    OWNER_ID_FIELD_NUMBER: _ClassVar[int]
    PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    owner_id: str
    project_id: str
    def __init__(self, owner_id: _Optional[str] = ..., project_id: _Optional[str] = ...) -> None: ...

class RunRequest(_message.Message):
    __slots__ = ("owner_id", "run_id")
    OWNER_ID_FIELD_NUMBER: _ClassVar[int]
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    owner_id: str
    run_id: str
    def __init__(self, owner_id: _Optional[str] = ..., run_id: _Optional[str] = ...) -> None: ...

class RunnerRequest(_message.Message):
    __slots__ = ("run_id",)
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    def __init__(self, run_id: _Optional[str] = ...) -> None: ...

class AddStepRequest(_message.Message):
    __slots__ = ("run_id", "index", "action", "ok", "locator", "value", "error")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    OK_FIELD_NUMBER: _ClassVar[int]
    LOCATOR_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    index: int
    action: str
    ok: bool
    locator: str
    value: str
    error: str
    def __init__(self, run_id: _Optional[str] = ..., index: _Optional[int] = ..., action: _Optional[str] = ..., ok: _Optional[bool] = ..., locator: _Optional[str] = ..., value: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...

class AddFindingRequest(_message.Message):
    __slots__ = ("run_id", "kind", "title", "details", "step_index")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    STEP_INDEX_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    kind: str
    title: str
    details: str
    step_index: int
    def __init__(self, run_id: _Optional[str] = ..., kind: _Optional[str] = ..., title: _Optional[str] = ..., details: _Optional[str] = ..., step_index: _Optional[int] = ...) -> None: ...

class AddTokensRequest(_message.Message):
    __slots__ = ("run_id", "count")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    count: int
    def __init__(self, run_id: _Optional[str] = ..., count: _Optional[int] = ...) -> None: ...

class SaveGeneratedTestRequest(_message.Message):
    __slots__ = ("run_id", "code")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    code: str
    def __init__(self, run_id: _Optional[str] = ..., code: _Optional[str] = ...) -> None: ...
