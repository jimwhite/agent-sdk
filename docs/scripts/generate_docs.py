#!/usr/bin/env python3
"""
Simple script to generate markdown documentation from Python modules.
"""

import importlib
import inspect
import os
import sys
from pathlib import Path
from typing import Any, Dict, List


def get_module_docstring(module: Any) -> str:
    """Get the docstring of a module."""
    return inspect.getdoc(module) or ""


def get_class_info(cls: type) -> Dict[str, Any]:
    """Get information about a class."""
    return {
        "name": cls.__name__,
        "docstring": inspect.getdoc(cls) or "",
        "methods": [
            {
                "name": name,
                "docstring": inspect.getdoc(method) or "",
                "signature": str(inspect.signature(method)) if callable(method) else "",
            }
            for name, method in inspect.getmembers(cls, inspect.ismethod)
            if not name.startswith("_")
        ],
        "functions": [
            {
                "name": name,
                "docstring": inspect.getdoc(func) or "",
                "signature": str(inspect.signature(func)),
            }
            for name, func in inspect.getmembers(cls, inspect.isfunction)
            if not name.startswith("_")
        ],
    }


def get_function_info(func: Any) -> Dict[str, Any]:
    """Get information about a function."""
    return {
        "name": func.__name__,
        "docstring": inspect.getdoc(func) or "",
        "signature": str(inspect.signature(func)),
    }


def generate_module_docs(module_name: str, output_dir: Path) -> None:
    """Generate markdown documentation for a module."""
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        print(f"Failed to import {module_name}: {e}")
        return

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    filename = module_name.replace(".", "_") + ".md"
    output_file = output_dir / filename

    with open(output_file, "w") as f:
        # Module header
        f.write(f"# {module_name}\n\n")

        # Module docstring
        module_doc = get_module_docstring(module)
        if module_doc:
            f.write(f"{module_doc}\n\n")

        # Classes
        classes = [
            (name, cls)
            for name, cls in inspect.getmembers(module, inspect.isclass)
            if cls.__module__ == module_name and not name.startswith("_")
        ]

        if classes:
            f.write("## Classes\n\n")
            for name, cls in classes:
                class_info = get_class_info(cls)
                f.write(f"### {name}\n\n")
                if class_info["docstring"]:
                    f.write(f"{class_info['docstring']}\n\n")

                # Methods
                if class_info["methods"]:
                    f.write("#### Methods\n\n")
                    for method in class_info["methods"]:
                        f.write(f"##### {method['name']}{method['signature']}\n\n")
                        if method["docstring"]:
                            f.write(f"{method['docstring']}\n\n")

                # Functions
                if class_info["functions"]:
                    f.write("#### Functions\n\n")
                    for func in class_info["functions"]:
                        f.write(f"##### {func['name']}{func['signature']}\n\n")
                        if func["docstring"]:
                            f.write(f"{func['docstring']}\n\n")

        # Module-level functions
        functions = [
            (name, func)
            for name, func in inspect.getmembers(module, inspect.isfunction)
            if func.__module__ == module_name and not name.startswith("_")
        ]

        if functions:
            f.write("## Functions\n\n")
            for name, func in functions:
                func_info = get_function_info(func)
                f.write(f"### {func_info['name']}{func_info['signature']}\n\n")
                if func_info["docstring"]:
                    f.write(f"{func_info['docstring']}\n\n")

    print(f"Generated documentation for {module_name} -> {output_file}")


def find_python_modules(package_path: Path) -> List[str]:
    """Find all Python modules in a package."""
    modules = []
    base_path = Path.cwd()

    for root, dirs, files in os.walk(package_path):
        # Skip __pycache__ directories and test directories
        dirs[:] = [d for d in dirs if d not in ["__pycache__", "tests"]]

        for file in files:
            if file.endswith(".py") and not file.startswith("_"):
                # Convert file path to module name
                root_path = Path(root).resolve()
                try:
                    rel_path = root_path.relative_to(base_path)
                    module_parts = list(rel_path.parts) + [
                        file[:-3]
                    ]  # Remove .py extension
                    module_name = ".".join(module_parts)
                    modules.append(module_name)
                except ValueError:
                    # If relative path fails, use absolute approach
                    continue

    return modules


def main():
    """Main function."""
    # Add current directory to Python path
    sys.path.insert(0, str(Path.cwd()))

    output_dir = Path("docs/reference")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate docs for SDK and tools
    packages = ["openhands/sdk", "openhands/tools"]

    for package in packages:
        package_path = Path(package)
        if package_path.exists():
            modules = find_python_modules(package_path)
            for module in modules:
                generate_module_docs(module, output_dir)

    # Create README
    readme_path = output_dir / "README.md"
    with open(readme_path, "w") as f:
        f.write("# API Reference\n\n")
        f.write("This section is generated from docstrings. Do not edit manually.\n\n")
        f.write("## Available Modules\n\n")

        # List all generated files
        for md_file in sorted(output_dir.glob("*.md")):
            if md_file.name != "README.md":
                module_name = md_file.stem.replace("_", ".")
                f.write(f"- [{module_name}]({md_file.name})\n")


if __name__ == "__main__":
    main()
