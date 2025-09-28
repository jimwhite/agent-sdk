"""Shell execution utilities for OpenHands SDK.

This module provides core shell execution functionality that can be reused
across different components of the OpenHands SDK, including local system mixins
and agent servers.
"""

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path

from openhands.sdk.logger import get_logger


logger = get_logger(__name__)

MAX_CONTENT_CHAR_LENGTH = 1024 * 1024


@dataclass
class ShellOutput:
    """Represents output from a shell command execution."""

    stdout: str | None = None
    stderr: str | None = None
    exit_code: int | None = None
    order: int = 0


@dataclass
class ShellExecutionResult:
    """Result of shell command execution."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    timeout_occurred: bool = False


async def execute_shell_command(
    command: str,
    cwd: str | Path | None = None,
    timeout: float = 30.0,
    output_callback: Callable[[ShellOutput], None] | None = None,
) -> ShellExecutionResult:
    """Execute a shell command asynchronously.

    This function provides the core shell execution logic that can be reused
    across different components. It handles:
    - Subprocess creation and management
    - Stdout/stderr streaming with buffering
    - Timeout handling and process termination
    - Output chunking for large outputs

    Args:
        command: The shell command to execute
        cwd: Working directory for the command (defaults to current directory)
        timeout: Timeout in seconds (defaults to 30.0)
        output_callback: Optional callback to receive output chunks as they arrive

    Returns:
        ShellExecutionResult containing the command result

    Raises:
        Exception: If there's an error creating or managing the subprocess
    """
    logger.debug(f"Executing shell command: {command}")

    try:
        # Create subprocess
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True,
        )

        # Track output order and buffers
        output_order = 0
        stdout_buffer = ""
        stderr_buffer = ""
        timeout_occurred = False

        async def read_stream(stream, is_stderr=False):
            nonlocal output_order, stdout_buffer, stderr_buffer

            buffer = stderr_buffer if is_stderr else stdout_buffer

            while True:
                try:
                    # Read data from stream
                    data = await stream.read(8192)  # Read in chunks
                    if not data:
                        break

                    text = data.decode("utf-8", errors="replace")
                    buffer += text

                    # Update the appropriate buffer
                    if is_stderr:
                        stderr_buffer = buffer
                    else:
                        stdout_buffer = buffer

                    # Check if we need to split the output
                    while len(buffer) > MAX_CONTENT_CHAR_LENGTH:
                        # Split at the max length
                        chunk = buffer[:MAX_CONTENT_CHAR_LENGTH]
                        buffer = buffer[MAX_CONTENT_CHAR_LENGTH:]

                        # Create output chunk and call callback if provided
                        if output_callback:
                            output = ShellOutput(
                                stdout=chunk if not is_stderr else None,
                                stderr=chunk if is_stderr else None,
                                order=output_order,
                            )
                            output_callback(output)

                        output_order += 1

                        # Update the appropriate buffer
                        if is_stderr:
                            stderr_buffer = buffer
                        else:
                            stdout_buffer = buffer

                except Exception as e:
                    logger.error(f"Error reading from stream: {e}")
                    break

        # Execute the entire command with timeout
        try:
            # Run stream reading and process waiting concurrently with timeout
            await asyncio.wait_for(
                asyncio.gather(
                    read_stream(process.stdout, is_stderr=False),
                    read_stream(process.stderr, is_stderr=True),
                    process.wait(),
                    return_exceptions=True,
                ),
                timeout=timeout,
            )
            exit_code = process.returncode
        except TimeoutError:
            timeout_occurred = True
            # Kill the process if it times out
            process.kill()
            try:
                # Give the process a short time to die gracefully
                await asyncio.wait_for(process.wait(), timeout=1.0)
            except TimeoutError:
                # If it still won't die, terminate it more forcefully
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=1.0)
                except TimeoutError:
                    logger.error(f"Failed to kill process for command: {command}")
            exit_code = -1
            logger.warning(f"Command timed out after {timeout} seconds: {command}")

        # Send final output if there's remaining buffer content
        if output_callback and (
            stdout_buffer or stderr_buffer or exit_code is not None
        ):
            final_output = ShellOutput(
                stdout=stdout_buffer if stdout_buffer else None,
                stderr=stderr_buffer if stderr_buffer else None,
                exit_code=exit_code if exit_code is not None else -1,
                order=output_order,
            )
            output_callback(final_output)

        return ShellExecutionResult(
            command=command,
            exit_code=exit_code if exit_code is not None else -1,
            stdout=stdout_buffer,
            stderr=stderr_buffer,
            timeout_occurred=timeout_occurred,
        )

    except Exception as e:
        logger.error(f"Error executing shell command '{command}': {e}")
        error_result = ShellExecutionResult(
            command=command,
            exit_code=-1,
            stdout="",
            stderr=f"Error executing command: {str(e)}",
            timeout_occurred=False,
        )

        # Send error output via callback if provided
        if output_callback:
            error_output = ShellOutput(
                stderr=error_result.stderr,
                exit_code=-1,
                order=0,
            )
            output_callback(error_output)

        return error_result


async def execute_shell_command_streaming(
    command: str,
    cwd: str | Path | None = None,
    timeout: float = 30.0,
) -> AsyncIterator[ShellOutput]:
    """Execute a shell command and yield output chunks as they arrive.

    This is a streaming version of execute_shell_command that yields
    ShellOutput objects as they are produced.

    Args:
        command: The shell command to execute
        cwd: Working directory for the command
        timeout: Timeout in seconds

    Yields:
        ShellOutput: Output chunks as they arrive

    Raises:
        Exception: If there's an error creating or managing the subprocess
    """
    output_queue = asyncio.Queue()

    def output_callback(output: ShellOutput):
        try:
            output_queue.put_nowait(output)
        except asyncio.QueueFull:
            logger.warning("Output queue is full, dropping output chunk")

    # Start the execution task
    execution_task = asyncio.create_task(
        execute_shell_command(command, cwd, timeout, output_callback)
    )

    try:
        # Yield outputs as they arrive
        while not execution_task.done():
            try:
                output = await asyncio.wait_for(output_queue.get(), timeout=0.1)
                yield output
            except TimeoutError:
                continue

        # Get any remaining outputs
        while not output_queue.empty():
            yield output_queue.get_nowait()

        # Wait for the execution to complete and handle any exceptions
        await execution_task

    except Exception as e:
        # Cancel the execution task if we encounter an error
        execution_task.cancel()
        try:
            await execution_task
        except asyncio.CancelledError:
            pass
        raise e
