"""Small, deterministic check against an independent automation practice site."""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from app.application.codegen import generate_test
from app.domain.entities import Action, Job, ProblemKind
from app.infra.browser import SiteBrowser

BASE_URL = "https://the-internet.herokuapp.com"
CASES = (("/javascript_error", ProblemKind.JS_ERROR), ("/status_codes/404", ProblemKind.HTTP_ERROR))


async def check(output: Path) -> bool:
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for index, (path, expected_kind) in enumerate(CASES):
        action = Action(name="goto", value=path)
        async with SiteBrowser(BASE_URL, allow_internal=False) as browser:
            result = await browser.perform(action)
            problems = browser.take_problems()
        matched = any(
            p.kind == expected_kind
            and (
                "404" in p.title and path in p.title
                if expected_kind == ProblemKind.HTTP_ERROR
                else "Cannot read properties" in p.title or "xyz" in p.title
            )
            for p in problems
        )
        results.append(
            {
                "url": BASE_URL + path,
                "expected_kind": expected_kind,
                "navigation_ok": result.ok,
                "navigation_error": result.error,
                "passed": matched,
                "findings": [
                    {"kind": p.kind, "title": p.title, "details": p.details} for p in problems
                ],
            }
        )
        job = Job(
            run_id=f"external-{index}",
            owner_id="external",
            project_id="the-internet",
            base_url=BASE_URL,
        )
        (output / f"test_external_{index}.py").write_text(
            generate_test(job, [action]), encoding="utf-8"
        )
    report = {
        "checked_at": datetime.now(UTC).isoformat(),
        "mode": "deterministic, no LLM",
        "results": results,
    }
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return all(r["passed"] for r in results)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/external"))
    args = parser.parse_args()
    raise SystemExit(0 if asyncio.run(check(args.output)) else 1)


if __name__ == "__main__":
    main()
