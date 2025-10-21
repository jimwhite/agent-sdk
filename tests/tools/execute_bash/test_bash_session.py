"""
Tests for bash session functionality across all terminal implementations.

This test suite uses pytest parametrization to run the same tests against all
available terminal implementations (subprocess, tmux, powershell) to ensure
consistent behavior across different backends.

The tests automatically detect which terminal types are available on the system
and run the parametrized tests for each one.
"""

import os
import tempfile
import time

import pytest

from openhands.sdk import TextContent
from openhands.sdk.logger import get_logger
from openhands.tools.execute_bash.definition import ExecuteBashAction
from openhands.tools.execute_bash.terminal import (
    TerminalCommandStatus,
    create_terminal_session,
)

from .conftest import get_no_change_timeout_suffix


logger = get_logger(__name__)

# Parametrize tests to run on all available terminal types
terminal_types = ["tmux", "subprocess"]
parametrize_terminal_types = pytest.mark.parametrize("terminal_type", terminal_types)


@parametrize_terminal_types
def test_session_initialization(terminal_type):
    # Test with custom working directory
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_terminal_session(
            work_dir=temp_dir, terminal_type=terminal_type
        )
        session.initialize()
        obs = session.execute(ExecuteBashAction(command="pwd"))

        assert temp_dir in obs.output
        assert "[The command completed with exit code 0.]" in obs.metadata.suffix
        session.close()

    # Test with custom username
    session = create_terminal_session(
        work_dir=os.getcwd(), username="nobody", terminal_type=terminal_type
    )
    session.initialize()
    session.close()


@parametrize_terminal_types
def test_cwd_property(tmp_path, terminal_type):
    session = create_terminal_session(work_dir=tmp_path, terminal_type=terminal_type)
    session.initialize()
    # Change directory and verify pwd updates
    random_dir = tmp_path / "random"
    random_dir.mkdir()
    session.execute(ExecuteBashAction(command=f"cd {random_dir}"))

    # For other implementations, just verify the command executed successfully
    obs = session.execute(ExecuteBashAction(command="pwd"))
    assert str(random_dir) in obs.output

    # Note: CWD tracking may vary between terminal implementations
    # For tmux, it should track properly. For subprocess, it may not.
    # if terminal_type == "tmux":
    assert session.cwd == str(random_dir)
    # else:
    session.close()


@parametrize_terminal_types
def test_basic_command(terminal_type):
    session = create_terminal_session(work_dir=os.getcwd(), terminal_type=terminal_type)
    session.initialize()

    # Test simple command
    obs = session.execute(ExecuteBashAction(command="echo 'hello world'"))

    assert "hello world" in obs.output
    assert obs.metadata.suffix == "\n[The command completed with exit code 0.]"
    # Note: prefix may vary between terminal implementations
    assert obs.metadata.exit_code == 0
    assert session.prev_status == TerminalCommandStatus.COMPLETED

    # Test command with error
    obs = session.execute(ExecuteBashAction(command="nonexistent_command"))

    # Note: Exit code handling may vary between terminal implementations
    # The important thing is that the error message is captured
    assert "nonexistent_command: command not found" in obs.output
    assert session.prev_status == TerminalCommandStatus.COMPLETED

    # Test multiple commands in sequence
    obs = session.execute(
        ExecuteBashAction(command='echo "first" && echo "second" && echo "third"')
    )
    assert "first" in obs.output
    assert "second" in obs.output
    assert "third" in obs.output
    assert obs.metadata.suffix == "\n[The command completed with exit code 0.]"
    # Note: prefix may vary between terminal implementations
    assert obs.metadata.exit_code == 0
    assert session.prev_status == TerminalCommandStatus.COMPLETED

    session.close()


@parametrize_terminal_types
def test_environment_variable_persistence(terminal_type):
    """Test that environment variables persist across commands (stateful terminal)."""
    session = create_terminal_session(work_dir=os.getcwd(), terminal_type=terminal_type)
    session.initialize()

    # Set an environment variable
    obs = session.execute(ExecuteBashAction(command="export TEST_VAR='hello world'"))
    assert obs.metadata.exit_code == 0

    # Use the environment variable in a subsequent command
    obs = session.execute(ExecuteBashAction(command="echo $TEST_VAR"))
    assert "hello world" in obs.output
    assert obs.metadata.exit_code == 0

    session.close()


@parametrize_terminal_types
def test_environment_variable_inheritance_from_parent(terminal_type):
    """Test that environment variables from parent process are inherited."""
    # Set an environment variable in the current process
    test_var_name = "OPENHANDS_TEST_INHERITANCE_VAR"
    test_var_value = "inherited_from_parent_12345"
    original_value = os.environ.get(test_var_name)

    try:
        # Set the environment variable in the parent process
        os.environ[test_var_name] = test_var_value

        # Create a new terminal session
        session = create_terminal_session(
            work_dir=os.getcwd(), terminal_type=terminal_type
        )
        session.initialize()

        # Check if the environment variable is available in the terminal
        obs = session.execute(ExecuteBashAction(command=f"echo ${test_var_name}"))
        assert test_var_value in obs.output, (
            f"Expected '{test_var_value}' in output, but got: {obs.output}"
        )
        assert obs.metadata.exit_code == 0

        session.close()

    finally:
        # Clean up: restore original environment variable value
        if original_value is not None:
            os.environ[test_var_name] = original_value
        else:
            os.environ.pop(test_var_name, None)


@pytest.mark.timeout(60)  # Add 60 second timeout to prevent hanging in CI
def test_long_running_command_follow_by_execute():
    session = create_terminal_session(work_dir=os.getcwd(), no_change_timeout_seconds=2)
    session.initialize()

    # Test command that produces output slowly
    obs = session.execute(
        ExecuteBashAction(command="echo 1; sleep 3; echo 2; sleep 3; echo 3")
    )

    assert "1" in obs.output  # First number should appear before timeout
    assert obs.metadata.exit_code == -1  # -1 indicates command is still running
    assert session.prev_status == TerminalCommandStatus.NO_CHANGE_TIMEOUT
    assert obs.metadata.suffix == get_no_change_timeout_suffix(2)
    assert obs.metadata.prefix == ""

    # Continue watching output
    obs = session.execute(ExecuteBashAction(command="", is_input=True))

    assert "2" in obs.output
    assert obs.metadata.prefix == "[Below is the output of the previous command.]\n"
    assert obs.metadata.suffix == get_no_change_timeout_suffix(2)
    assert obs.metadata.exit_code == -1  # -1 indicates command is still running
    assert session.prev_status == TerminalCommandStatus.NO_CHANGE_TIMEOUT

    # Test command that produces no output
    obs = session.execute(ExecuteBashAction(command="sleep 15"))

    assert "3" not in obs.output
    assert obs.metadata.prefix == "[Below is the output of the previous command.]\n"
    assert "The previous command is still running" in obs.metadata.suffix
    assert obs.metadata.exit_code == -1  # -1 indicates command is still running
    assert session.prev_status == TerminalCommandStatus.NO_CHANGE_TIMEOUT

    time.sleep(3)

    # Run it again, this time it should produce output and then start a new command
    obs = session.execute(ExecuteBashAction(command="sleep 15"))

    assert "3" in obs.output  # Should see the final output from the previous command
    assert obs.metadata.exit_code == -1  # -1 indicates new command is still running
    assert session.prev_status == TerminalCommandStatus.NO_CHANGE_TIMEOUT

    session.close()


@parametrize_terminal_types
@pytest.mark.timeout(60)  # Add 60 second timeout to prevent hanging in CI
def test_interactive_command(terminal_type):
    session = create_terminal_session(
        work_dir=os.getcwd(), no_change_timeout_seconds=3, terminal_type=terminal_type
    )
    session.initialize()

    # Test interactive command with blocking=True
    obs = session.execute(
        ExecuteBashAction(
            command="read -p 'Enter name: ' name && echo \"Hello $name\"",
        )
    )

    assert "Enter name:" in obs.output
    assert obs.metadata.exit_code == -1  # -1 indicates command is still running
    assert session.prev_status == TerminalCommandStatus.NO_CHANGE_TIMEOUT
    assert obs.metadata.suffix == get_no_change_timeout_suffix(3)
    assert obs.metadata.prefix == ""

    # Send input
    obs = session.execute(ExecuteBashAction(command="John", is_input=True))

    assert "Hello John" in obs.output
    assert obs.metadata.exit_code == 0
    assert obs.metadata.suffix == "\n[The command completed with exit code 0.]"
    assert obs.metadata.prefix == ""
    assert session.prev_status == TerminalCommandStatus.COMPLETED

    # Test multiline command input
    obs = session.execute(ExecuteBashAction(command="cat << EOF"))

    assert obs.metadata.exit_code == -1
    assert session.prev_status == TerminalCommandStatus.NO_CHANGE_TIMEOUT
    assert obs.metadata.suffix == get_no_change_timeout_suffix(3)
    assert obs.metadata.prefix == ""

    obs = session.execute(ExecuteBashAction(command="line 1", is_input=True))

    assert obs.metadata.exit_code == -1
    assert session.prev_status == TerminalCommandStatus.NO_CHANGE_TIMEOUT
    assert obs.metadata.suffix == get_no_change_timeout_suffix(3)
    assert obs.metadata.prefix == "[Below is the output of the previous command.]\n"

    obs = session.execute(ExecuteBashAction(command="line 2", is_input=True))

    assert obs.metadata.exit_code == -1
    assert session.prev_status == TerminalCommandStatus.NO_CHANGE_TIMEOUT
    assert obs.metadata.suffix == get_no_change_timeout_suffix(3)
    assert obs.metadata.prefix == "[Below is the output of the previous command.]\n"

    obs = session.execute(ExecuteBashAction(command="EOF", is_input=True))

    assert "line 1" in obs.output and "line 2" in obs.output
    assert obs.metadata.exit_code == 0
    assert obs.metadata.suffix == "\n[The command completed with exit code 0.]"
    assert obs.metadata.prefix == ""

    session.close()


@parametrize_terminal_types
@pytest.mark.timeout(60)  # Add 60 second timeout to prevent hanging in CI
def test_ctrl_c(terminal_type):
    session = create_terminal_session(
        work_dir=os.getcwd(), no_change_timeout_seconds=2, terminal_type=terminal_type
    )
    session.initialize()

    # Start infinite loop
    obs = session.execute(
        ExecuteBashAction(command="while true; do echo 'looping'; sleep 3; done"),
    )

    assert "looping" in obs.output
    assert obs.metadata.suffix == get_no_change_timeout_suffix(2)
    assert obs.metadata.prefix == ""
    assert obs.metadata.exit_code == -1  # -1 indicates command is still running
    assert session.prev_status == TerminalCommandStatus.NO_CHANGE_TIMEOUT

    # Send Ctrl+C
    obs = session.execute(ExecuteBashAction(command="C-c", is_input=True))

    # Check that the process was interrupted (exit code can be 1 or 130
    # depending on the shell/OS)
    assert obs.metadata.exit_code in (
        1,
        130,
    )  # Accept both common exit codes for interrupted processes
    assert "CTRL+C was sent" in obs.metadata.suffix
    assert obs.metadata.prefix == ""
    assert session.prev_status == TerminalCommandStatus.COMPLETED

    session.close()


@parametrize_terminal_types
def test_empty_command_error(terminal_type):
    session = create_terminal_session(work_dir=os.getcwd(), terminal_type=terminal_type)
    session.initialize()

    # Test empty command without previous command
    obs = session.execute(ExecuteBashAction(command=""))

    assert obs.error is True
    assert obs.output == "ERROR: No previous running command to retrieve logs from."
    assert len(obs.to_llm_content) == 1
    assert isinstance(obs.to_llm_content[0], TextContent)
    assert "There was an error during command execution." in obs.to_llm_content[0].text
    assert (
        "ERROR: No previous running command to retrieve logs from."
        in obs.to_llm_content[0].text
    )
    assert obs.metadata.exit_code == -1
    assert obs.metadata.prefix == ""
    assert obs.metadata.suffix == ""
    assert session.prev_status is None

    session.close()


@parametrize_terminal_types
@pytest.mark.timeout(60)  # Add 60 second timeout to prevent hanging in CI
def test_command_output_continuation(terminal_type):
    """Test that we can continue to get output from a long-running command.

    This test has been modified to be more robust against timing issues.
    """
    session = create_terminal_session(
        work_dir=os.getcwd(), no_change_timeout_seconds=1, terminal_type=terminal_type
    )
    session.initialize()

    # Start a command that produces output slowly but with longer sleep time
    # to ensure we hit the timeout
    obs = session.execute(
        ExecuteBashAction(command="for i in {1..5}; do echo $i; sleep 2; done")
    )

    # Check if the command completed immediately or timed out
    if session.prev_status == TerminalCommandStatus.COMPLETED:
        # If the command completed immediately, verify we got all the output
        logger.info("Command completed immediately", extra={"msg_type": "TEST_INFO"})
        assert "1" in obs.output
        assert "2" in obs.output
        assert "3" in obs.output
        assert "4" in obs.output
        assert "5" in obs.output
        assert "[The command completed with exit code 0.]" in obs.metadata.suffix
    else:
        # If the command timed out, verify we got the timeout message
        assert session.prev_status == TerminalCommandStatus.NO_CHANGE_TIMEOUT
        assert "1" in obs.output
        assert "[The command has no new output after 1 seconds." in obs.metadata.suffix

        # Continue getting output until we see all numbers
        numbers_seen = set()
        for i in range(1, 6):
            if str(i) in obs.output:
                numbers_seen.add(i)

        # We need to see numbers 2-5 and then the command completion
        while (
            len(numbers_seen) < 5
            or session.prev_status != TerminalCommandStatus.COMPLETED
        ):
            obs = session.execute(ExecuteBashAction(command="", is_input=True))

            # Check for numbers in the output
            for i in range(1, 6):
                if str(i) in obs.output and i not in numbers_seen:
                    numbers_seen.add(i)
                    logger.info(
                        f"Found number {i} in output", extra={"msg_type": "TEST_INFO"}
                    )

            # Check if the command has completed
            if session.prev_status == TerminalCommandStatus.COMPLETED:
                assert (
                    "[The command completed with exit code 0.]" in obs.metadata.suffix
                )
                break
            else:
                assert (
                    "[The command has no new output after 1 seconds."
                    in obs.metadata.suffix
                )
                assert session.prev_status == TerminalCommandStatus.NO_CHANGE_TIMEOUT

        # Verify we've seen all numbers
        assert numbers_seen == {1, 2, 3, 4, 5}, (
            f"Expected to see numbers 1-5, but saw {numbers_seen}"
        )

        # Verify the command completed
        assert session.prev_status == TerminalCommandStatus.COMPLETED

    session.close()


@parametrize_terminal_types
def test_long_output(terminal_type):
    session = create_terminal_session(work_dir=os.getcwd(), terminal_type=terminal_type)
    session.initialize()

    # Generate a long output that may exceed buffer size
    obs = session.execute(
        ExecuteBashAction(command='for i in {1..5000}; do echo "Line $i"; done')
    )

    assert "Line 1" in obs.output
    assert "Line 5000" in obs.output
    assert obs.metadata.exit_code == 0
    assert obs.metadata.prefix == ""
    assert obs.metadata.suffix == "\n[The command completed with exit code 0.]"

    session.close()


@parametrize_terminal_types
def test_long_output_exceed_history_limit(terminal_type):
    session = create_terminal_session(work_dir=os.getcwd(), terminal_type=terminal_type)
    session.initialize()

    # Generate a long output that may exceed buffer size
    obs = session.execute(
        ExecuteBashAction(command='for i in {1..50000}; do echo "Line $i"; done')
    )

    assert "Previous command outputs are truncated" in obs.metadata.prefix
    assert "Line 40000" in obs.output
    assert "Line 50000" in obs.output
    assert obs.metadata.exit_code == 0
    assert obs.metadata.suffix == "\n[The command completed with exit code 0.]"

    session.close()


def test_multiline_command():
    session = create_terminal_session(work_dir=os.getcwd())
    session.initialize()

    # Test multiline command with PS2 prompt disabled
    obs = session.execute(
        ExecuteBashAction(
            command="""if true; then
echo "inside if"
fi""",
        )
    )

    assert "inside if" in obs.output
    assert obs.metadata.exit_code == 0
    assert obs.metadata.prefix == ""
    assert obs.metadata.suffix == "\n[The command completed with exit code 0.]"

    session.close()


@parametrize_terminal_types
def test_python_interactive_input(terminal_type):
    session = create_terminal_session(
        work_dir=os.getcwd(), no_change_timeout_seconds=2, terminal_type=terminal_type
    )
    session.initialize()

    # Test Python program that asks for input - properly escaped for bash
    python_script = (
        "name = input('Enter your name: '); age = input('Enter your age: '); "
        "print(f'Hello {name}, you are {age} years old')"
    )

    # Start Python with the interactive script
    obs = session.execute(ExecuteBashAction(command=f'python3 -c "{python_script}"'))

    assert "Enter your name:" in obs.output
    assert obs.metadata.exit_code == -1  # -1 indicates command is still running
    assert session.prev_status == TerminalCommandStatus.NO_CHANGE_TIMEOUT

    # Send first input (name)
    obs = session.execute(ExecuteBashAction(command="Alice", is_input=True))

    assert "Enter your age:" in obs.output
    assert obs.metadata.exit_code == -1
    assert session.prev_status == TerminalCommandStatus.NO_CHANGE_TIMEOUT

    # Send second input (age)
    obs = session.execute(ExecuteBashAction(command="25", is_input=True))

    assert "Hello Alice, you are 25 years old" in obs.output
    assert obs.metadata.exit_code == 0
    assert obs.metadata.suffix == "\n[The command completed with exit code 0.]"
    assert session.prev_status == TerminalCommandStatus.COMPLETED

    session.close()


def _run_bash_action(session, command: str, **kwargs):
    """Helper function to execute a bash command and return the observation."""
    action = ExecuteBashAction(command=command, **kwargs)
    obs = session.execute(action)
    logger.info(f"Command: {command}")
    logger.info(f"Output: {obs.output}")
    logger.info(f"Exit code: {obs.metadata.exit_code}")
    return obs


@parametrize_terminal_types
def test_bash_server(terminal_type):
    """Test running a server with timeout and interrupt."""
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_terminal_session(
            work_dir=temp_dir, terminal_type=terminal_type
        )
        session.initialize()
        try:
            # Use python -u for unbuffered output, potentially helping
            # capture initial output on Windows
            obs = _run_bash_action(
                session, "python -u -m http.server 8081", timeout=1.0
            )
            assert obs.metadata.exit_code == -1
            assert "Serving HTTP on" in obs.output

            # Send Ctrl+C to interrupt
            obs = _run_bash_action(session, "C-c", is_input=True)
            assert "CTRL+C was sent" in obs.metadata.suffix
            assert "Keyboard interrupt received, exiting." in obs.output

            # Verify we can run commands after interrupt
            obs = _run_bash_action(session, "ls")
            assert obs.metadata.exit_code == 0

            # Run server again to verify it works
            obs = _run_bash_action(
                session, "python -u -m http.server 8081", timeout=1.0
            )
            assert obs.metadata.exit_code == -1
            assert "Serving HTTP on" in obs.output

        finally:
            session.close()


@parametrize_terminal_types
def test_bash_background_server(terminal_type):
    """Test running a server in background."""
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_terminal_session(
            work_dir=temp_dir, terminal_type=terminal_type
        )
        session.initialize()
        server_port = 8081
        try:
            # Start the server in background
            obs = _run_bash_action(session, f"python3 -m http.server {server_port} &")
            assert obs.metadata.exit_code == 0

            # Give the server a moment to be ready
            time.sleep(1)

            # Verify the server is running by curling it
            obs = _run_bash_action(session, f"curl http://localhost:{server_port}")
            assert obs.metadata.exit_code == 0
            # Check for content typical of python http.server directory listing
            assert "Directory listing for" in obs.output

            # Kill the server
            obs = _run_bash_action(session, 'pkill -f "http.server"')
            assert obs.metadata.exit_code == 0

        finally:
            session.close()


@parametrize_terminal_types
def test_multiline_commands(terminal_type):
    """Test multiline command execution."""
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_terminal_session(
            work_dir=temp_dir, terminal_type=terminal_type
        )
        session.initialize()
        try:
            # Original Linux bash version
            # single multiline command
            obs = _run_bash_action(session, 'echo \\\n -e "foo"')
            assert obs.metadata.exit_code == 0
            assert "foo" in obs.output

            # test multiline echo
            obs = _run_bash_action(session, 'echo -e "hello\nworld"')
            assert obs.metadata.exit_code == 0
            assert "hello\nworld" in obs.output

            # test whitespace
            obs = _run_bash_action(session, 'echo -e "a\\n\\n\\nz"')
            assert obs.metadata.exit_code == 0
            assert "\n\n\n" in obs.output
        finally:
            session.close()


@parametrize_terminal_types
def test_complex_commands(terminal_type):
    """Test complex bash command execution."""
    cmd = (
        'count=0; tries=0; while [ $count -lt 3 ]; do result=$(echo "Heads"); '
        'tries=$((tries+1)); echo "Flip $tries: $result"; '
        'if [ "$result" = "Heads" ]; then count=$((count+1)); else count=0; fi; '
        'done; echo "Got 3 heads in a row after $tries flips!";'
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_terminal_session(
            work_dir=temp_dir, terminal_type=terminal_type
        )
        session.initialize()
        try:
            obs = _run_bash_action(session, cmd)
            assert obs.metadata.exit_code == 0
            assert "Got 3 heads in a row after 3 flips!" in obs.output
        finally:
            session.close()


@parametrize_terminal_types
def test_no_ps2_in_output(terminal_type):
    """Test that the PS2 sign is not added to the output of a multiline command."""
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_terminal_session(
            work_dir=temp_dir, terminal_type=terminal_type
        )
        session.initialize()
        try:
            obs = _run_bash_action(session, 'echo -e "hello\nworld"')
            assert obs.metadata.exit_code == 0

            assert "hello\nworld" in obs.output
            assert ">" not in obs.output
        finally:
            session.close()


@parametrize_terminal_types
def test_multiline_command_loop(terminal_type):
    """Test multiline command with loops."""
    # https://github.com/OpenHands/OpenHands/issues/3143
    init_cmd = """mkdir -p _modules && \\
for month in {01..04}; do
    for day in {01..05}; do
        touch "_modules/2024-${month}-${day}-sample.md"
    done
done && echo "created files"
"""
    follow_up_cmd = """for file in _modules/*.md; do
    new_date=$(echo $file | sed -E \\
        's/2024-(01|02|03|04)-/2024-/;s/2024-01/2024-08/;s/2024-02/2024-09/;s/2024-03/2024-10/;s/2024-04/2024-11/')
    mv "$file" "$new_date"
done && echo "success"
"""
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_terminal_session(
            work_dir=temp_dir, terminal_type=terminal_type
        )
        session.initialize()
        try:
            obs = _run_bash_action(session, init_cmd)
            assert obs.metadata.exit_code == 0
            assert "created files" in obs.output

            obs = _run_bash_action(session, follow_up_cmd)
            assert obs.metadata.exit_code == 0
            assert "success" in obs.output
        finally:
            session.close()


@parametrize_terminal_types
def test_multiple_multiline_commands(terminal_type):
    """Test that multiple commands separated by newlines are rejected."""
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_terminal_session(
            work_dir=temp_dir, terminal_type=terminal_type
        )
        session.initialize()
        try:
            cmds = [
                "ls -l",
                'echo -e "hello\nworld"',
                """echo -e "hello it's me\"""",
                """echo \\
-e 'hello' \\
world""",
                """echo -e 'hello\\nworld\\nare\\nyou\\nthere?'""",
                """echo -e 'hello\nworld\nare\nyou\n\nthere?'""",
                """echo -e 'hello\nworld "'""",
            ]
            joined_cmds = "\n".join(cmds)

            # First test that running multiple commands at once fails
            obs = _run_bash_action(session, joined_cmds)
            assert obs.error is True
            assert "Cannot execute multiple commands at once" in obs.output

            # Now run each command individually and verify they work
            results = []
            for cmd in cmds:
                obs = _run_bash_action(session, cmd)
                assert obs.metadata.exit_code == 0
                results.append(obs.output)

            # Verify all expected outputs are present
            assert "total 0" in results[0]  # ls -l
            assert "hello\nworld" in results[1]  # echo -e "hello\nworld"
            assert "hello it's me" in results[2]  # echo -e "hello it\'s me"
            assert "hello world" in results[3]  # echo -e 'hello' world
            assert (
                "hello\nworld\nare\nyou\nthere?" in results[4]
            )  # echo -e 'hello\nworld\nare\nyou\nthere?'
            assert (
                "hello\nworld\nare\nyou\n\nthere?" in results[5]
            )  # echo -e with literal newlines
            assert 'hello\nworld "' in results[6]  # echo -e with quote
        finally:
            session.close()


@parametrize_terminal_types
def test_cmd_run(terminal_type):
    """Test basic command execution."""
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_terminal_session(
            work_dir=temp_dir, terminal_type=terminal_type
        )
        session.initialize()
        try:
            # Unix version
            obs = _run_bash_action(session, f"ls -l {temp_dir}")
            assert obs.metadata.exit_code == 0

            obs = _run_bash_action(session, "ls -l")
            assert obs.metadata.exit_code == 0
            assert "total 0" in obs.output

            obs = _run_bash_action(session, "mkdir test")
            assert obs.metadata.exit_code == 0

            obs = _run_bash_action(session, "ls -l")
            assert obs.metadata.exit_code == 0
            assert "test" in obs.output

            obs = _run_bash_action(session, "touch test/foo.txt")
            assert obs.metadata.exit_code == 0

            obs = _run_bash_action(session, "ls -l test")
            assert obs.metadata.exit_code == 0
            assert "foo.txt" in obs.output

            # clean up
            _run_bash_action(session, "rm -rf test")
            assert obs.metadata.exit_code == 0
        finally:
            session.close()


@parametrize_terminal_types
def test_run_as_user_correct_home_dir(terminal_type):
    """Test that home directory is correct."""
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_terminal_session(
            work_dir=temp_dir, terminal_type=terminal_type
        )
        session.initialize()
        try:
            # Original Linux version
            obs = _run_bash_action(session, "cd ~ && pwd")
            assert obs.metadata.exit_code == 0
            home = os.getenv("HOME")
            assert home and home in obs.output
        finally:
            session.close()


@parametrize_terminal_types
def test_multi_cmd_run_in_single_line(terminal_type):
    """Test multiple commands in a single line."""
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_terminal_session(work_dir=temp_dir)
        session.initialize()
        try:
            # Original Linux version using &&
            obs = _run_bash_action(session, "pwd && ls -l")
            assert obs.metadata.exit_code == 0
            assert temp_dir in obs.output
            assert "total 0" in obs.output
        finally:
            session.close()


@parametrize_terminal_types
def test_stateful_cmd(terminal_type):
    """Test that commands maintain state across executions."""
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_terminal_session(
            work_dir=temp_dir, terminal_type=terminal_type
        )
        session.initialize()
        try:
            # Original Linux version
            obs = _run_bash_action(session, "mkdir -p test")
            assert obs.metadata.exit_code == 0

            obs = _run_bash_action(session, "cd test")
            assert obs.metadata.exit_code == 0

            obs = _run_bash_action(session, "pwd")
            assert obs.metadata.exit_code == 0
            assert f"{temp_dir}/test" in obs.output.strip()
        finally:
            session.close()


@parametrize_terminal_types
def test_failed_cmd(terminal_type):
    """Test failed command execution."""
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_terminal_session(
            work_dir=temp_dir, terminal_type=terminal_type
        )
        session.initialize()
        try:
            obs = _run_bash_action(session, "non_existing_command")
            assert obs.metadata.exit_code != 0
        finally:
            session.close()


@parametrize_terminal_types
def test_python_version(terminal_type):
    """Test Python version command."""
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_terminal_session(
            work_dir=temp_dir, terminal_type=terminal_type
        )
        session.initialize()
        try:
            obs = _run_bash_action(session, "python --version")
            assert obs.metadata.exit_code == 0
            assert "Python 3" in obs.output
        finally:
            session.close()


@parametrize_terminal_types
def test_pwd_property(terminal_type):
    """Test pwd property updates."""
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_terminal_session(
            work_dir=temp_dir, terminal_type=terminal_type
        )
        session.initialize()
        try:
            # Create a subdirectory and verify pwd updates
            obs = _run_bash_action(session, "mkdir -p random_dir")
            assert obs.metadata.exit_code == 0

            obs = _run_bash_action(session, "cd random_dir && pwd")
            assert obs.metadata.exit_code == 0
            assert "random_dir" in obs.output
        finally:
            session.close()


@parametrize_terminal_types
@pytest.mark.timeout(180)  # Add 3 minute timeout for this intensive test
def test_long_output_from_nested_directories(terminal_type):
    """Test long output from nested directory operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_terminal_session(
            work_dir=temp_dir, terminal_type=terminal_type
        )
        session.initialize()
        try:
            # Create nested directories with many files
            setup_cmd = (
                "mkdir -p /tmp/test_dir && cd /tmp/test_dir && "
                'for i in $(seq 1 100); do mkdir -p "folder_$i"; '
                'for j in $(seq 1 100); do touch "folder_$i/file_$j.txt"; done; done'
            )
            obs = _run_bash_action(session, setup_cmd.strip(), timeout=60)
            assert obs.metadata.exit_code == 0

            # List the directory structure recursively
            obs = _run_bash_action(session, "ls -R /tmp/test_dir", timeout=60)
            assert obs.metadata.exit_code == 0

            # Verify output contains expected files
            assert "folder_1" in obs.output
            assert "file_1.txt" in obs.output
            assert "folder_100" in obs.output
            assert "file_100.txt" in obs.output
        finally:
            session.close()


@parametrize_terminal_types
def test_command_backslash(terminal_type):
    """Test command with backslash escaping."""
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_terminal_session(
            work_dir=temp_dir, terminal_type=terminal_type
        )
        session.initialize()
        try:
            # Create a file with the content "implemented_function"
            cmd = (
                "mkdir -p /tmp/test_dir && "
                'echo "implemented_function" > /tmp/test_dir/file_1.txt'
            )
            obs = _run_bash_action(session, cmd)
            assert obs.metadata.exit_code == 0

            # Different escaping for different terminal types
            if terminal_type == "subprocess":
                semicolon = '";"'  # No escaping needed for subprocess
            else:
                semicolon = "\\;"  # Escape for tmux

            cmd = (
                "find /tmp/test_dir -type f -exec grep"
                + f' -l "implemented_function" {{}} {semicolon}'
            )
            obs = _run_bash_action(session, cmd)
            assert obs.metadata.exit_code == 0
            assert "/tmp/test_dir/file_1.txt" in obs.output
        finally:
            session.close()


@parametrize_terminal_types
def test_bash_remove_prefix(terminal_type):
    """Test bash command prefix removal."""
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_terminal_session(
            work_dir=temp_dir, terminal_type=terminal_type
        )
        session.initialize()
        try:
            # create a git repo - same for both platforms
            obs = _run_bash_action(
                session,
                "git init && git remote add origin https://github.com/OpenHands/OpenHands",
            )
            assert obs.metadata.exit_code == 0

            # Check git remote - same for both platforms
            obs = _run_bash_action(session, "git remote -v")
            assert obs.metadata.exit_code == 0
            assert "https://github.com/OpenHands/OpenHands" in obs.output
            assert "git remote -v" not in obs.output
        finally:
            session.close()
