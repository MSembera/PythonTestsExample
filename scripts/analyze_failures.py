"""Summarize pytest JUnit XML failures using Claude and write a Markdown report.

Advisory only, never fails the CI job: if ANTHROPIC_API_KEY is unset, or a
Claude call errors, this logs a notice/per-failure error and exits 0.
"""

import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import anthropic

MODEL = "claude-sonnet-5"
# Pytest tracebacks can run to thousands of characters (long local variable
# dumps); the assertion itself is almost always at the end, so keep the tail.
MAX_TRACEBACK_CHARS = 6000
MAX_SOURCE_CHARS = 8000
# Pytest's short traceback ends with "path/to/file.py:123: ExceptionType" -
# the last such line is the closest frame to the actual failure.
_TRACEBACK_LOCATION_RE = re.compile(r"^(?P<path>.+\.py):(?P<line>\d+):", re.MULTILINE)

SYSTEM_PROMPT = (
    "You are reviewing a failed pytest test from an automated API/UI test suite "
    "for a web application. Given the test name, its failure output (assertion "
    "message and traceback), and - when available - the source of the failing "
    "test file, write a short root-cause analysis and a concrete suggested fix. "
    "Keep it to a few sentences plus, if useful, a short code snippet. If the "
    "failure looks like flakiness in the app under test rather than a bug in "
    "the test code, say so."
)


def parse_failures(junit_xml_path: Path) -> list[dict[str, str]]:
    root = ET.parse(junit_xml_path).getroot()
    failures = []
    for testcase in root.iter("testcase"):
        outcome = testcase.find("failure")
        if outcome is None:
            outcome = testcase.find("error")
        if outcome is None:
            continue
        traceback = (outcome.text or "").strip()
        if len(traceback) > MAX_TRACEBACK_CHARS:
            traceback = "...(truncated)...\n" + traceback[-MAX_TRACEBACK_CHARS:]
        failures.append(
            {
                "name": f"{testcase.get('classname', '')}::{testcase.get('name', '')}",
                "message": outcome.get("message", ""),
                "traceback": traceback,
            }
        )
    return failures


def find_test_source(traceback: str) -> str | None:
    """Read the source of the file at the last "path.py:line:" seen in the traceback.

    Best-effort: returns None if the traceback has no such location, the path
    doesn't resolve to a real file under the current working directory (the
    repo root when run in CI), or it can't be read.
    """
    matches = list(_TRACEBACK_LOCATION_RE.finditer(traceback))
    if not matches:
        return None
    path = Path(matches[-1].group("path")).resolve()
    if not path.is_relative_to(Path.cwd().resolve()) or not path.is_file():
        return None
    source = path.read_text(encoding="utf-8", errors="replace")
    if len(source) > MAX_SOURCE_CHARS:
        source = source[:MAX_SOURCE_CHARS] + "\n...(truncated)..."
    return source


def analyze(client: anthropic.Anthropic, failure: dict[str, str], source: str | None) -> str:
    content = (
        f"Test: {failure['name']}\n"
        f"Message: {failure['message']}\n\n"
        f"Traceback:\n{failure['traceback']}"
    )
    if source is not None:
        content += f"\n\nTest file source:\n{source}"

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        output_config={"effort": "low"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )
    return next(block.text for block in response.content if block.type == "text")


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: analyze_failures.py <junit_xml_path> <output_markdown_path>")
        return 1
    junit_xml_path, output_path = Path(sys.argv[1]), Path(sys.argv[2])

    if not junit_xml_path.exists():
        print(f"No JUnit report at {junit_xml_path}, skipping AI analysis.")
        return 0

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set, skipping AI analysis.")
        return 0

    failures = parse_failures(junit_xml_path)
    if not failures:
        print("No failures in report, nothing to analyze.")
        return 0

    client = anthropic.Anthropic()
    sections = []
    for failure in failures:
        print(f"Analyzing {failure['name']}...")
        source = find_test_source(failure["traceback"])
        try:
            analysis = analyze(client, failure, source)
        except Exception as exc:  # advisory tooling: one bad call shouldn't skip the rest
            analysis = f"_AI analysis failed: {exc}_"
        sections.append(f"## {failure['name']}\n\n{analysis}\n")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("# AI Failure Analysis\n\n" + "\n".join(sections))
    print(f"Wrote analysis for {len(failures)} failure(s) to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
