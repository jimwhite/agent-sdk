"""Tests for the TODO scanner functionality."""

# Import the scanner functions
import sys
import tempfile
from pathlib import Path


todo_mgmt_path = (
    Path(__file__).parent.parent.parent 
    / "examples" / "github_workflows" / "02_todo_management"
)
sys.path.append(str(todo_mgmt_path))
from todo_scanner import scan_directory, scan_file_for_todos  # noqa: E402


def test_scan_python_file_with_todos():
    """Test scanning a Python file with TODO comments."""
    content = '''#!/usr/bin/env python3
"""Test file with TODOs."""

def function1():
    # TODO(openhands): Add input validation
    return "hello"

def function2():
    # TODO(openhands): Implement error handling for network requests
    pass

# Regular comment, should be ignored
# TODO: Regular todo, should be ignored
# TODO(other): Other todo, should be ignored
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(content)
        f.flush()
        
        todos = scan_file_for_todos(Path(f.name))
    
    # Clean up
    Path(f.name).unlink()
    
    assert len(todos) == 2
    
    # Check first TODO
    assert todos[0]['line'] == 5
    assert todos[0]['description'] == 'Add input validation'
    assert 'TODO(openhands): Add input validation' in todos[0]['content']
    
    # Check second TODO
    assert todos[1]['line'] == 9
    assert todos[1]['description'] == 'Implement error handling for network requests'
    expected_content = 'TODO(openhands): Implement error handling for network requests'
    assert expected_content in todos[1]['content']


def test_scan_javascript_file_with_todos():
    """Test scanning a JavaScript file with TODO comments."""
    content = '''// JavaScript file with TODOs
function processData(data) {
    // TODO(openhands): Add data validation
    return data.map(item => item.value);
}

/* TODO(openhands): Implement caching mechanism */
function fetchData() {
    return fetch('/api/data');
}
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(content)
        f.flush()
        
        todos = scan_file_for_todos(Path(f.name))
    
    # Clean up
    Path(f.name).unlink()
    
    assert len(todos) == 2
    assert todos[0]['description'] == 'Add data validation'
    assert todos[1]['description'] == 'Implement caching mechanism'


def test_scan_file_with_processed_todos():
    """Test that TODOs with PR URLs are skipped."""
    content = '''def function1():
    # TODO(openhands: https://github.com/owner/repo/pull/123): Already processed
    return "hello"

def function2():
    # TODO(openhands): Still needs processing
    pass
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(content)
        f.flush()
        
        todos = scan_file_for_todos(Path(f.name))
    
    # Clean up
    Path(f.name).unlink()
    
    # Should only find the unprocessed TODO
    assert len(todos) == 1
    assert todos[0]['description'] == 'Still needs processing'


def test_scan_markdown_file_filters_examples():
    """Test that markdown documentation examples are filtered out."""
    content = '''# Documentation

Use TODO comments like this:

- `# TODO(openhands): description` (Python, Shell, etc.)
- `// TODO(openhands): description` (JavaScript, C++, etc.)

Example usage:
```python
# TODO(openhands): Add error handling
def process():
    pass
```

This is a real TODO that should be found:
# TODO(openhands): Update this documentation section
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        f.flush()
        
        todos = scan_file_for_todos(Path(f.name))
    
    # Clean up
    Path(f.name).unlink()
    
    # Should only find the real TODO, not the examples
    assert len(todos) == 1
    assert todos[0]['description'] == 'Update this documentation section'


def test_scan_binary_file():
    """Test that binary files are skipped."""
    # Create a binary file
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.bin', delete=False) as f:
        f.write(b'\x00\x01\x02\x03# TODO(openhands): This should not be found')
        f.flush()
        
        todos = scan_file_for_todos(Path(f.name))
    
    # Clean up
    Path(f.name).unlink()
    
    # Should find no TODOs in binary file
    assert len(todos) == 0


def test_scan_directory():
    """Test scanning a directory with multiple files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create Python file with TODO
        py_file = temp_path / "test.py"
        py_file.write_text('''def func():
    # TODO(openhands): Fix this function
    pass
''')
        
        # Create JavaScript file with TODO
        js_file = temp_path / "test.js"
        js_file.write_text('''function test() {
    // TODO(openhands): Add validation
    return true;
}
''')
        
        # Create file without TODOs
        no_todo_file = temp_path / "clean.py"
        no_todo_file.write_text('''def clean_function():
    return "no todos here"
''')
        
        # Create subdirectory with TODO
        sub_dir = temp_path / "subdir"
        sub_dir.mkdir()
        sub_file = sub_dir / "sub.py"
        sub_file.write_text('''# TODO(openhands): Subdirectory TODO
def sub_func():
    pass
''')
        
        todos = scan_directory(temp_path)
    
    # Should find 3 TODOs total
    assert len(todos) == 3
    
    # Check that all files are represented
    files = {todo['file'] for todo in todos}
    assert str(py_file) in files
    assert str(js_file) in files
    assert str(sub_file) in files
    assert str(no_todo_file) not in files


def test_todo_context_extraction():
    """Test that context lines are properly extracted."""
    content = '''def function():
    """Function docstring."""
    x = 1
    y = 2
    # TODO(openhands): Add error handling
    z = x + y
    return z
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(content)
        f.flush()
        
        todos = scan_file_for_todos(Path(f.name))
    
    # Clean up
    Path(f.name).unlink()
    
    assert len(todos) == 1
    todo = todos[0]
    
    # Check context
    assert len(todo['context']['before']) == 3
    assert len(todo['context']['after']) == 2
    assert 'x = 1' in todo['context']['before']
    assert 'z = x + y' in todo['context']['after']


def test_empty_file():
    """Test scanning an empty file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('')
        f.flush()
        
        todos = scan_file_for_todos(Path(f.name))
    
    # Clean up
    Path(f.name).unlink()
    
    assert len(todos) == 0


def test_file_with_unicode():
    """Test scanning a file with unicode characters."""
    content = '''# -*- coding: utf-8 -*-
def process_unicode():
    # TODO(openhands): Handle unicode strings properly
    return "Hello 世界"
'''
    
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.py', delete=False, encoding='utf-8'
    ) as f:
        f.write(content)
        f.flush()
        
        todos = scan_file_for_todos(Path(f.name))
    
    # Clean up
    Path(f.name).unlink()
    
    assert len(todos) == 1
    assert todos[0]['description'] == 'Handle unicode strings properly'