"""Tests for the automated TODO management example."""

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


# Add the project root to the path so we can import openhands.sdk
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the module directly
spec = importlib.util.spec_from_file_location(
    "automated_todo_management",
    Path(__file__).parent.parent / "20_automated_todo_management.py",
)
assert spec is not None, "Could not load module spec"
assert spec.loader is not None, "Module spec has no loader"
todo_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(todo_module)

# Import the classes
TodoItem = todo_module.TodoItem
TodoScanner = todo_module.TodoScanner
GitHubPRManager = todo_module.GitHubPRManager
AutomatedTodoManager = todo_module.AutomatedTodoManager


class TestTodoItem:
    """Test the TodoItem dataclass."""

    def test_todo_item_creation(self):
        """Test creating a TodoItem."""
        todo = TodoItem(
            file_path="test.py",
            line_number=10,
            todo_text="add unit tests",
            context_before=["def function():"],
            context_after=["    pass"],
            full_context=(
                "def function():\n    # TODO(openhands): add unit tests\n    pass"
            ),
            unique_id="",
        )

        assert todo.file_path == "test.py"
        assert todo.line_number == 10
        assert todo.todo_text == "add unit tests"
        assert todo.unique_id  # Should be generated automatically
        assert len(todo.unique_id) == 8  # MD5 hash truncated to 8 chars

    def test_todo_item_unique_id_generation(self):
        """Test that unique IDs are generated consistently."""
        todo1 = TodoItem(
            file_path="test.py",
            line_number=10,
            todo_text="add unit tests",
            context_before=[],
            context_after=[],
            full_context="",
            unique_id="",
        )

        todo2 = TodoItem(
            file_path="test.py",
            line_number=10,
            todo_text="add unit tests",
            context_before=[],
            context_after=[],
            full_context="",
            unique_id="",
        )

        # Same content should generate same ID
        assert todo1.unique_id == todo2.unique_id

        # Different content should generate different ID
        todo3 = TodoItem(
            file_path="test.py",
            line_number=11,  # Different line
            todo_text="add unit tests",
            context_before=[],
            context_after=[],
            full_context="",
            unique_id="",
        )

        assert todo1.unique_id != todo3.unique_id


class TestTodoScanner:
    """Test the TodoScanner class."""

    def test_scan_repository_finds_todos(self):
        """Test that the scanner finds TODO comments."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test Python file with TODO comments
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
def function1():
    # TODO(openhands): add unit tests
    pass

def function2():
    # TODO(openhands): implement error handling
    return None

def function3():
    # TODO(openhands-in-progress): this should be ignored
    pass

def function4():
    # Regular TODO comment - should be ignored
    # TODO: fix this later
    pass
""")

            scanner = TodoScanner(temp_dir)
            todos = scanner.scan_repository()

            assert len(todos) == 2

            # Check first TODO
            todo1 = todos[0]
            assert todo1.file_path == "test.py"
            assert todo1.line_number == 3
            assert todo1.todo_text == "add unit tests"
            assert "def function1():" in todo1.full_context

            # Check second TODO
            todo2 = todos[1]
            assert todo2.file_path == "test.py"
            assert todo2.line_number == 7
            assert todo2.todo_text == "implement error handling"
            assert "def function2():" in todo2.full_context

    def test_scan_repository_excludes_directories(self):
        """Test that the scanner excludes certain directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files in excluded directories
            venv_dir = Path(temp_dir) / ".venv" / "lib"
            venv_dir.mkdir(parents=True)
            venv_file = venv_dir / "test.py"
            venv_file.write_text("# TODO(openhands): should be ignored")

            cache_dir = Path(temp_dir) / "__pycache__"
            cache_dir.mkdir()
            cache_file = cache_dir / "test.py"
            cache_file.write_text("# TODO(openhands): should be ignored")

            # Create file in included directory
            main_file = Path(temp_dir) / "main.py"
            main_file.write_text("# TODO(openhands): should be found")

            scanner = TodoScanner(temp_dir)
            todos = scanner.scan_repository()

            assert len(todos) == 1
            assert todos[0].file_path == "main.py"

    def test_scan_repository_handles_encoding_errors(self):
        """Test that the scanner handles files with encoding issues gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file with valid content
            good_file = Path(temp_dir) / "good.py"
            good_file.write_text("# TODO(openhands): valid todo")

            # Create a file with binary content (will cause encoding error)
            bad_file = Path(temp_dir) / "bad.py"
            bad_file.write_bytes(b"\x80\x81\x82\x83")

            scanner = TodoScanner(temp_dir)
            todos = scanner.scan_repository()

            # Should find the valid TODO and skip the problematic file
            assert len(todos) == 1
            assert todos[0].file_path == "good.py"


class TestGitHubPRManager:
    """Test the GitHubPRManager class."""

    def test_init(self):
        """Test GitHubPRManager initialization."""
        manager = GitHubPRManager("owner", "repo", "token")

        assert manager.repo_owner == "owner"
        assert manager.repo_name == "repo"
        assert manager.github_token == "token"
        assert manager.base_url == "https://api.github.com"
        assert "token token" in manager.headers["Authorization"]

    @patch("requests.get")
    @patch("requests.post")
    def test_create_branch_success(self, mock_post, mock_get):
        """Test successful branch creation."""
        # Mock getting base branch SHA
        mock_get.return_value.json.return_value = {"object": {"sha": "abc123"}}
        mock_get.return_value.raise_for_status.return_value = None

        # Mock creating branch
        mock_post.return_value.raise_for_status.return_value = None

        manager = GitHubPRManager("owner", "repo", "token")
        result = manager.create_branch("test-branch")

        assert result is True
        mock_get.assert_called_once()
        mock_post.assert_called_once()

    @patch("requests.get")
    def test_create_branch_failure(self, mock_get):
        """Test branch creation failure."""
        mock_get.side_effect = Exception("API Error")

        manager = GitHubPRManager("owner", "repo", "token")
        result = manager.create_branch("test-branch")

        assert result is False

    @patch("requests.post")
    def test_create_pull_request_success(self, mock_post):
        """Test successful PR creation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "html_url": "https://github.com/owner/repo/pull/1",
            "number": 1,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        manager = GitHubPRManager("owner", "repo", "token")
        result = manager.create_pull_request("branch", "title", "body")

        assert result is not None
        assert result["html_url"] == "https://github.com/owner/repo/pull/1"
        assert result["number"] == 1

    @patch("requests.get")
    def test_check_existing_prs(self, mock_get):
        """Test checking for existing PRs."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {"head": {"ref": "openhands/todo-abc123"}},
            {"head": {"ref": "feature/other-branch"}},
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        manager = GitHubPRManager("owner", "repo", "token")

        # Should find existing PR
        assert manager.check_existing_prs("abc123") is True

        # Should not find non-existing PR
        assert manager.check_existing_prs("xyz789") is False


class TestAutomatedTodoManager:
    """Test the AutomatedTodoManager class."""

    def test_load_config_default(self):
        """Test loading default configuration."""
        with patch.object(todo_module, "TodoImplementer"):
            manager = AutomatedTodoManager(
                repo_path="/tmp",
                repo_owner="owner",
                repo_name="repo",
                github_token="token",
                llm=Mock(),
                config_path=None,
            )

            config = manager.config
            assert config["max_todos_per_run"] == 3
            assert config["branch_prefix"] == "openhands/todo-"
            assert "exclude_patterns" in config

    def test_load_config_from_file(self):
        """Test loading configuration from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {
                "max_todos_per_run": 5,
                "branch_prefix": "custom/todo-",
                "custom_setting": "value",
            }
            json.dump(config_data, f)
            config_path = f.name

        try:
            with patch.object(todo_module, "TodoImplementer"):
                manager = AutomatedTodoManager(
                    repo_path="/tmp",
                    repo_owner="owner",
                    repo_name="repo",
                    github_token="token",
                    llm=Mock(),
                    config_path=config_path,
                )

                config = manager.config
                assert config["max_todos_per_run"] == 5
                assert config["branch_prefix"] == "custom/todo-"
                assert config["custom_setting"] == "value"
                # Should still have defaults
                assert "exclude_patterns" in config
        finally:
            os.unlink(config_path)

    def test_run_dry_run(self):
        """Test running in dry-run mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file with TODO
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("# TODO(openhands): test todo")

            with patch.object(todo_module, "TodoImplementer"):
                manager = AutomatedTodoManager(
                    repo_path=temp_dir,
                    repo_owner="owner",
                    repo_name="repo",
                    github_token="token",
                    llm=Mock(),
                )

                result = manager.run(dry_run=True)

                assert result["status"] == "success"
                assert "Found 1 TODOs" in result["message"]
                assert len(result["todos"]) == 1
                assert result["todos"][0]["file"] == "test.py"
                assert result["todos"][0]["text"] == "test todo"

    def test_run_no_todos(self):
        """Test running when no TODOs are found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file without TODOs
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("# Regular comment")

            with patch.object(todo_module, "TodoImplementer"):
                manager = AutomatedTodoManager(
                    repo_path=temp_dir,
                    repo_owner="owner",
                    repo_name="repo",
                    github_token="token",
                    llm=Mock(),
                )

                result = manager.run()

                assert result["status"] == "success"
                assert result["message"] == "No TODOs found"
                assert result["todos_processed"] == 0

    def test_mark_todo_in_progress(self):
        """Test marking a TODO as in progress."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file with TODO
            test_file = Path(temp_dir) / "test.py"
            original_content = "# TODO(openhands): test todo\npass"
            test_file.write_text(original_content)

            todo = TodoItem(
                file_path="test.py",
                line_number=1,
                todo_text="test todo",
                context_before=[],
                context_after=["pass"],
                full_context=original_content,
                unique_id="test123",
            )

            with patch.object(todo_module, "TodoImplementer"):
                manager = AutomatedTodoManager(
                    repo_path=temp_dir,
                    repo_owner="owner",
                    repo_name="repo",
                    github_token="token",
                    llm=Mock(),
                )

                manager._mark_todo_in_progress(todo)

                # Check that the file was updated
                updated_content = test_file.read_text()
                assert "TODO(openhands-in-progress):" in updated_content
                assert "TODO(openhands):" not in updated_content

    def test_unmark_todo_in_progress(self):
        """Test unmarking a TODO as in progress."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file with in-progress TODO
            test_file = Path(temp_dir) / "test.py"
            original_content = "# TODO(openhands-in-progress): test todo\npass"
            test_file.write_text(original_content)

            todo = TodoItem(
                file_path="test.py",
                line_number=1,
                todo_text="test todo",
                context_before=[],
                context_after=["pass"],
                full_context=original_content,
                unique_id="test123",
            )

            with patch.object(todo_module, "TodoImplementer"):
                manager = AutomatedTodoManager(
                    repo_path=temp_dir,
                    repo_owner="owner",
                    repo_name="repo",
                    github_token="token",
                    llm=Mock(),
                )

                manager._unmark_todo_in_progress(todo)

                # Check that the file was reverted
                updated_content = test_file.read_text()
                assert "TODO(openhands):" in updated_content
                assert "TODO(openhands-in-progress):" not in updated_content


@pytest.fixture
def sample_todo():
    """Fixture providing a sample TodoItem for testing."""
    return TodoItem(
        file_path="example.py",
        line_number=42,
        todo_text="implement feature X",
        context_before=["def some_function():", "    # Setup code"],
        context_after=["    pass", "    return None"],
        full_context=(
            "def some_function():\n    # Setup code\n    "
            "# TODO(openhands): implement feature X\n    pass\n    return None"
        ),
        unique_id="abc12345",
    )


def test_sample_todo_fixture(sample_todo):
    """Test that the sample_todo fixture works correctly."""
    assert sample_todo.file_path == "example.py"
    assert sample_todo.line_number == 42
    assert sample_todo.todo_text == "implement feature X"
    assert sample_todo.unique_id == "abc12345"
