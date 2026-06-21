#!/usr/bin/env python3
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def escape(value):
    return (
        str(value or "").replace("%", "%25").replace("\n", "%0A").replace("\r", "%0D")
    )


def emit_error(path, line, title, message):
    print(f"::error file={path},line={line},title={escape(title)}::{escape(message)}")


def annotate_junit(path):
    if not path.exists():
        return 0

    count = 0
    root = ET.parse(path).getroot()
    for case in root.iter("testcase"):
        failure = case.find("failure")
        problem = failure if failure is not None else case.find("error")
        if problem is None:
            continue
        name = f"{case.get('classname')}.{case.get('name')}"
        emit_error(
            case.get("file") or ".github",
            case.get("line") or "1",
            name,
            problem.get("message") or problem.text or "pytest failure",
        )
        count += 1
    return count


def annotate_tail(path):
    if not path.exists():
        emit_error(
            ".github/workflows/ci.yml",
            "1",
            "pytest failed",
            "No pytest output captured.",
        )
        return

    lines = path.read_text(errors="replace").splitlines()
    tail = "\n".join(lines[-120:])
    emit_error(".github/workflows/ci.yml", "1", "pytest failed", tail)


def main():
    output_path = Path(sys.argv[1])
    junit_path = Path(sys.argv[2])
    if annotate_junit(junit_path) == 0:
        annotate_tail(output_path)


if __name__ == "__main__":
    main()
