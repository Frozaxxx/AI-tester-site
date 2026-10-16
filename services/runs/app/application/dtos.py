from dataclasses import dataclass

from app.domain.entities import Finding, GeneratedTest, Run, Step


@dataclass
class RunDetails:
    run: Run
    steps: list[Step]
    findings: list[Finding]
    test: GeneratedTest | None
