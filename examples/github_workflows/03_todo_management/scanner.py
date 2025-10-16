#!/usr/bin/env python3
"""
TODO Scanner for OpenHands Automated TODO Management

Scans for `# TODO(openhands)` comments in Python, TypeScript, and Java files.
"""

import argparse
import json
import os
import re
from pathlib import Path


def scan_file_for_todos(file_path: Path) -> list[dict]:
    """Scan a single file for TODO(openhands) comments."""
    # Only scan specific file extensions
    if file_path.suffix.lower() not in {".py", ".ts", ".java"}:
        return []

    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return []

    todos = []
    todo_pattern = re.compile(r"TODO\(openhands\)(?::\s*(.*))?", re.IGNORECASE)

    for line_num, line in enumerate(lines, 1):
        match = todo_pattern.search(line)
        if match and "pull/" not in line:  # Skip already processed TODOs
            description = match.group(1).strip() if match.group(1) else ""
            todos.append(
                {
                    "file": str(file_path),
                    "line": line_num,
                    "text": line.strip(),
                    "description": description,
                }
            )

    return todos


def scan_directory(directory: Path) -> list[dict]:
    """Recursively scan a directory for TODO(openhands) comments."""
    all_todos = []

    for root, dirs, files in os.walk(directory):
        # Skip hidden and common ignore directories
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".")
            and d
            not in {"__pycache__", "node_modules", ".venv", "venv", "build", "dist"}
        ]

        for file in files:
            file_path = Path(root) / file
            todos = scan_file_for_todos(file_path)
            all_todos.extend(todos)

    return all_todos


def main():
    """Main function to scan for TODOs and output results."""
    parser = argparse.ArgumentParser(
        description="Scan codebase for TODO(openhands) comments"
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory to scan (default: current directory)",
    )
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")

    args = parser.parse_args()

    directory = Path(args.directory)
    if not directory.exists():
        print(f"Error: Directory '{directory}' does not exist")
        return 1

    todos = scan_directory(directory)
    output = json.dumps(todos, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Found {len(todos)} TODO(s), written to {args.output}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    exit(main())
