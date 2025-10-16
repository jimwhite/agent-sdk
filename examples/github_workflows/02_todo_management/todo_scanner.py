#!/usr/bin/env python3
"""
TODO Scanner for OpenHands Automated TODO Management

This script scans a codebase for `# TODO(openhands)` comments and outputs
them in a structured format for processing by the TODO management workflow.

Usage:
    python todo_scanner.py [directory]

Arguments:
    directory: Directory to scan (default: current directory)

Output:
    JSON array of TODO items with file path, line number, and content
"""

import argparse
import json
import os
import re
from pathlib import Path


def is_binary_file(file_path: Path) -> bool:
    """Check if a file is binary by reading a small chunk."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\0' in chunk
    except OSError:
        return True


def should_skip_file(file_path: Path) -> bool:
    """Check if a file should be skipped during scanning."""
    # Skip common binary and generated file extensions
    skip_extensions = {
        '.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib',
        '.exe', '.bin', '.obj', '.o', '.a', '.lib',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico',
        '.mp3', '.mp4', '.avi', '.mov', '.wav',
        '.zip', '.tar', '.gz', '.bz2', '.xz',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx',
        '.lock', '.egg-info'
    }
    
    if file_path.suffix.lower() in skip_extensions:
        return True
    
    # Skip common directories
    skip_dirs = {
        '.git', '.svn', '.hg', '.bzr',
        '__pycache__', '.pytest_cache', '.mypy_cache',
        'node_modules', '.venv', 'venv', '.env',
        '.tox', '.coverage', 'htmlcov',
        'build', 'dist', '.egg-info',
        '.idea', '.vscode'
    }
    
    for part in file_path.parts:
        if part in skip_dirs:
            return True
    
    return False


def scan_file_for_todos(file_path: Path) -> list[dict]:
    """
    Scan a single file for TODO(openhands) comments.
    
    Returns:
        List of dictionaries containing TODO information
    """
    todos = []
    
    if should_skip_file(file_path) or is_binary_file(file_path):
        return todos
    
    try:
        with open(file_path, encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return todos
    
    # Pattern to match TODO(openhands) comments
    # Matches variations like:
    # # TODO(openhands): description
    # // TODO(openhands): description  
    # /* TODO(openhands): description */
    # <!-- TODO(openhands): description -->
    todo_pattern = re.compile(
        r'(?:#|//|/\*|<!--)\s*TODO\(openhands\)(?::\s*([^*\-]*))?(?:\*/|-->)?',
        re.IGNORECASE
    )
    
    for line_num, line in enumerate(lines, 1):
        match = todo_pattern.search(line.strip())
        if match:
            description = match.group(1).strip() if match.group(1) else ""
            
            # Check if this TODO already has a PR URL (indicating it's been processed)
            if "https://github.com/" in line and "/pull/" in line:
                continue  # Skip already processed TODOs
            
            # Skip documentation examples and comments in markdown files
            if file_path.suffix.lower() in {'.md', '.rst', '.txt'}:
                # Check if this looks like a documentation example
                line_content = line.strip()
                if (line_content.startswith('- `') or 
                    line_content.startswith('```') or
                    'example' in line_content.lower() or
                    'format' in line_content.lower()):
                    continue
            
            # Skip lines that appear to be in code blocks or examples
            stripped_line = line.strip()
            if (stripped_line.startswith('```') or 
                stripped_line.startswith('echo ') or
                'example' in stripped_line.lower()):
                continue
            
            todos.append({
                'file': str(file_path),
                'line': line_num,
                'content': line.strip(),
                'description': description,
                'context': {
                    'before': [
                        line.rstrip() 
                        for line in lines[max(0, line_num-3):line_num-1]
                    ],
                    'after': [
                        line.rstrip() 
                        for line in lines[line_num:min(len(lines), line_num+3)]
                    ]
                }
            })
    
    return todos


def scan_directory(directory: Path) -> list[dict]:
    """
    Recursively scan a directory for TODO(openhands) comments.
    
    Returns:
        List of all TODO items found
    """
    all_todos = []
    
    for root, dirs, files in os.walk(directory):
        # Skip hidden directories and common ignore patterns
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
            '__pycache__', 'node_modules', '.venv', 'venv', 'build', 'dist'
        }]
        
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
        help="Directory to scan (default: current directory)"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file (default: stdout)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)"
    )
    
    args = parser.parse_args()
    
    path = Path(args.directory).resolve()
    if not path.exists():
        print(f"Error: Path '{path}' does not exist")
        return 1
    
    if path.is_file():
        print(f"Scanning file: {path}", file=os.sys.stderr)
        todos = scan_file_for_todos(path)
    elif path.is_dir():
        print(f"Scanning directory: {path}", file=os.sys.stderr)
        todos = scan_directory(path)
    else:
        print(f"Error: '{path}' is neither a file nor a directory")
        return 1
    
    if args.format == "json":
        output = json.dumps(todos, indent=2)
    else:
        output_lines = []
        for todo in todos:
            output_lines.append(f"{todo['file']}:{todo['line']}: {todo['content']}")
            if todo['description']:
                output_lines.append(f"  Description: {todo['description']}")
            output_lines.append("")
        output = "\n".join(output_lines)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Results written to: {args.output}", file=os.sys.stderr)
    else:
        print(output)
    
    print(f"Found {len(todos)} TODO(openhands) items", file=os.sys.stderr)
    return 0


if __name__ == "__main__":
    exit(main())